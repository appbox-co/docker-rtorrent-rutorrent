#!/bin/sh
# Release gate for ruTorrent 5.3.15.8 (Dockerfile.autodl-themes): the 5.3.15.7
# image with an updated patch-autodl-rutorrent-html5.py that generates autodl
# stylesheets for club-QuickBox, DarkBetter, MaterialDesign and OblivionBlue,
# so the Filters window stays on screen with a long filter list.
#
# Usage: release/verify-autodl-image.sh <image>
#
#   <image> is repo.cylo.net/rutorrent:5.3.15.8-0.16.24 for a release, or a
#   local/rutorrent-trial:<tag> image for a trial run.
#
# Exits 0 only when the local image passes every check and the authenticated
# registry definitively reports that the release tag does not exist yet. The
# registry check always targets the release tag, whatever image is tested.
# Any indeterminate registry answer fails.
set -eu
LC_ALL=C
export LC_ALL

RELEASE_REF="repo.cylo.net/rutorrent:5.3.15.8-0.16.24"
RELEASE_VERSION="5.3.15.8"
BASE_NAME="5.3.15.7"
BASE_REF="repo.cylo.net/rutorrent@sha256:db1a64429462205a3bc41833e4886fc4205945b5115a907ae6bf303e087b9df6"
RUTORRENT_REVISION="fe468360f94b02def11bbf67b16316bbe8081380"
PHP_VERSION="8.5.13"
PLUGIN="/var/www/rutorrent/plugins/autodl-rutorrent"
PATCH_SCRIPT="/usr/local/bin/patch-autodl-rutorrent-html5.py"
GENERATED="club-quickbox darkbetter materialdesign oblivionblue"
EXTRA_LAYERS=2
HEALTH_TIMEOUT=900

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

[ "$#" -eq 1 ] || fail "usage: $0 <image>"
image_ref=$1
case "$image_ref" in
    "$RELEASE_REF") gate_mode=release ;;
    local/rutorrent-trial:*)
        case "${image_ref#local/rutorrent-trial:}" in
            ''|*[!A-Za-z0-9._-]*) fail "invalid trial tag: $image_ref" ;;
        esac
        gate_mode=trial
        ;;
    *) fail "unexpected image reference: $image_ref (expected $RELEASE_REF or local/rutorrent-trial:<tag>)" ;;
esac

release_dir=$(cd "$(dirname "$0")" && pwd)
repo_dir=$(dirname "$release_dir")
for tool in docker curl jq cmp diff od sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing tool: $tool"
done

run_id="rutorrent-autodl-gate-$(od -An -N6 -tx1 /dev/urandom | tr -d ' \n')"
gate_label="appbox.release-gate=$run_id"
work_dir=$(mktemp -d)
gate_containers=""
gate_volumes=""

cleanup() {
    for gate_container in $gate_containers; do
        owner=$(docker inspect --format '{{index .Config.Labels "appbox.release-gate"}}' "$gate_container" 2>/dev/null || true)
        [ "$owner" = "$run_id" ] && docker rm -fv "$gate_container" >/dev/null 2>&1 || true
    done
    for gate_volume in $gate_volumes; do
        owner=$(docker volume inspect --format '{{index .Labels "appbox.release-gate"}}' "$gate_volume" 2>/dev/null || true)
        [ "$owner" = "$run_id" ] && docker volume rm "$gate_volume" >/dev/null 2>&1 || true
    done
    rm -rf "$work_dir"
}
trap cleanup EXIT
trap 'exit 1' INT TERM

in_image() {
    gate_image=$1
    shift
    gate_entrypoint=$1
    shift
    docker run --rm --platform linux/amd64 --network none --entrypoint "$gate_entrypoint" "$gate_image" "$@"
}

registry_auth=""
registry_get() {
    printf 'header = "Authorization: Basic %s"\n' "$registry_auth" \
        | curl -sS --max-time 60 -K - -o "$work_dir/registry-body" -w '%{http_code}' \
            -H 'Accept: application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json' \
            "https://$1"
}

check_registry() {
    echo "== Registry: $RELEASE_REF must not exist"
    registry=${RELEASE_REF%%/*}
    repository_and_tag=${RELEASE_REF#*/}
    repository=${repository_and_tag%:*}
    tag=${repository_and_tag##*:}
    base_digest=${BASE_REF#*@}
    registry_auth=$(jq -r --arg host "$registry" '.auths[$host].auth // empty' "$HOME/.docker/config.json")
    [ -n "$registry_auth" ] || fail "no stored credentials for $registry"

    api_status=$(registry_get "$registry/v2/") || fail "registry unreachable"
    [ "$api_status" = 200 ] || fail "registry API check returned HTTP $api_status"
    known_status=$(registry_get "$registry/v2/$repository/manifests/$base_digest") || fail "registry unreachable"
    [ "$known_status" = 200 ] || fail "registry read of the $BASE_NAME digest returned HTTP $known_status; state is indeterminate"
    manifest_status=$(registry_get "$registry/v2/$repository/manifests/$tag") || fail "registry unreachable"
    case "$manifest_status" in
        200) fail "$RELEASE_REF already exists in the registry; refusing to replace it" ;;
        404)
            grep -q 'MANIFEST_UNKNOWN' "$work_dir/registry-body" \
                || fail "registry returned 404 without MANIFEST_UNKNOWN: $(head -c 300 "$work_dir/registry-body")"
            echo "$BASE_NAME digest readable; $RELEASE_REF is definitively absent (MANIFEST_UNKNOWN)"
            ;;
        *) fail "registry returned HTTP $manifest_status for $RELEASE_REF" ;;
    esac
}

show_logs() {
    docker logs --tail 80 "$1" 2>&1 | grep -v -i -E 'pass|token' >&2 || true
}

wait_healthy() {
    waited=0
    while :; do
        state=$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "$1")
        case "$state" in
            "running healthy") echo "$1 healthy after ${waited}s"; return 0 ;;
            exited*|dead*)
                show_logs "$1"
                fail "$1 stopped during startup: $state"
                ;;
        esac
        [ "$waited" -lt "$HEALTH_TIMEOUT" ] || {
            show_logs "$1"
            fail "$1 did not become healthy within ${HEALTH_TIMEOUT}s ($state)"
        }
        sleep 3
        waited=$((waited + 3))
    done
}

new_volume() {
    docker volume create --label "$gate_label" "$1" >/dev/null
    gate_volumes="$gate_volumes $1"
}

# The catalogue's app-level environment for app 66 (template values
# replaced with test values), so the containers run as Appbox runs them.
APPBOX_ENV="-e EXTERNAL_DOMAIN=https://rtorrent.example.test -e RU_HTTP_TIME_OUT=300
 -e RU_RPC_TIME_OUT=300 -e RU_CACHED_PLUGIN_LOADING=true -e RU_FORBID_USER_SETTINGS=false
 -e RT_INC_PORT=50000 -e RT_DHT_PORT=6881 -e WAN_IP=127.0.0.1 -e MEMORY_LIMIT=1G
 -e UPLOAD_MAX_SIZE=1000G -e REAL_IP_FROM=172.20.0.0/12 -e REAL_IP_HEADER=X-Real-IP
 -e RT_SESSION_SAVE_SECONDS=300 -e XMLRPC_SIZE_LIMIT=10M -e RT_PREALLOCATE_TYPE=1
 -e RT_SEND_BUFFER_SIZE=0 -e RT_RECEIVE_BUFFER_SIZE=0"

# start_app NAME IMAGE TORRENTS_VOLUME PASSWD_VOLUME
#   Passes the install fields RUTORRENT_USER and RUTORRENT_PASSWORD (the
#   password from the environment, not the command line).
start_app() {
    gate_containers="$gate_containers $1"
    # shellcheck disable=SC2086
    docker run -d --name "$1" --label "$gate_label" --platform linux/amd64 --network none \
        -e RUTORRENT_USER=releasegate -e RUTORRENT_PASSWORD $APPBOX_ENV -e SKIP_APPBOX_CALLBACK=1 \
        -v "$3:/torrents" -v "$4:/passwd" "$2" >/dev/null
    wait_healthy "$1"
    wait_rpc "$1"
}

# The image's healthcheck passes about ten seconds before ruTorrent is
# usable: .rtlocal.rc schedules ruTorrent's php/initplugins.php 10 s after
# rTorrent starts (schedule init_plugins), and addtorrent.php reports
# "Failed" until it has run (5.3.15.6 and 5.3.15.7 behave the same; see
# release/verify-image.sh). Wait until /RPC2 answers with the test login, the
# ratio plugin's groups (group.rat_0.*, created by initplugins.php) exist and
# no initplugins.php process is still running, before any check runs.
wait_rpc() {
    rpc_waited=0
    until docker exec -i -e USERNAME=releasegate -e PASSWORD "$1" python3 - >/dev/null 2>&1 <<'RPCPY'
import base64, os, subprocess, sys, urllib.request, xmlrpc.client
auth = base64.b64encode(("%s:%s" % (os.environ["USERNAME"], os.environ["PASSWORD"])).encode()).decode()
req = urllib.request.Request("http://127.0.0.1/RPC2", data=xmlrpc.client.dumps((), "system.listMethods").encode(),
                             method="POST", headers={"Content-Type": "text/xml", "Authorization": "Basic " + auth})
with urllib.request.urlopen(req, timeout=10) as resp:
    methods = xmlrpc.client.loads(resp.read())[0][0]
running = subprocess.run(["pgrep", "-f", "rutorrent/php/initplugins.php"], capture_output=True).stdout.strip()
sys.exit(0 if "group.rat_0.ratio.command" in methods and not running else 1)
RPCPY
    do
        [ "$rpc_waited" -lt 180 ] || fail "$1: ruTorrent plugins were not initialised within 180s"
        sleep 3
        rpc_waited=$((rpc_waited + 3))
    done
    echo "$1 rTorrent XML-RPC up and ruTorrent plugins initialised after ${rpc_waited}s"
}

# The checks sign in with USERNAME and PASSWORD from the docker exec environment.
runtime_check() {
    app_name=$1
    shift
    docker exec -i -e USERNAME=releasegate -e PASSWORD "$app_name" python3 - "$@" < "$release_dir/runtime-checks.py"
}

auth_check() {
    docker exec -i -e USERNAME=releasegate -e PASSWORD "$1" python3 - "$2" < "$release_dir/auth-checks.py"
}

theme_check() {
    docker exec -i -e USERNAME=releasegate -e PASSWORD "$1" python3 - served < "$release_dir/autodl-theme-checks.py"
}

seed() {
    for seed_attempt in 1 2 3; do
        if seed_output=$(runtime_check "$1" seed 2>&1); then
            printf '%s\n' "$seed_output" | tail -n 1 | jq -r '.seeded'
            return 0
        fi
        printf '%s\n' "$seed_output" | tail -n 3 >&2
        echo "seed attempt $seed_attempt failed; retrying in 20s" >&2
        sleep 20
    done
    return 1
}

# step DESCRIPTION COMMAND...: run one check; on failure show the end of its
# output and fail the gate, otherwise print its last line (the JSON summary).
step() {
    step_description=$1
    shift
    step_output=$("$@" 2>&1) || {
        printf '%s\n' "$step_output" | tail -n 20 >&2
        fail "$step_description"
    }
    printf '%s\n' "$step_output" | tail -n 1
}

# Persistent state an upgrade must keep: .rtorrent.rc, the session's
# .torrent files, a file under /torrents/completed, the selected theme and
# the autodl configuration.
volume_state() {
    docker exec "$1" sh -c 'set -e
        sha256sum /torrents/config/rtorrent/.rtorrent.rc /torrents/completed/appbox-gate-marker.txt \
            /torrents/config/rutorrent/share/users/releasegate/settings/theme.dat /torrents/config/autodl/autodl.cfg
        cd /torrents/config/rtorrent/.session
        for f in *.torrent; do [ -f "$f" ] && echo "$f"; done'
}

THEME_DAT='O:6:"rTheme":3:{s:4:"hash";s:9:"theme.dat";s:8:"modified";b:0;s:7:"current";s:13:"club-QuickBox";}'

echo "== Gate $run_id: $image_ref ($gate_mode)"
grep -q "^  version: \"$RELEASE_VERSION\"\$" "$repo_dir/appbox.yml" \
    && grep -q "^  tag: \"${RELEASE_REF##*:}\"\$" "$repo_dir/appbox.yml" \
    || fail "appbox.yml image.version/tag do not match $RELEASE_REF"
check_registry

echo "== Image identity"
docker image inspect "$image_ref" >/dev/null 2>&1 || fail "$image_ref is not a local image"
docker image inspect "$BASE_REF" >/dev/null 2>&1 || docker pull --platform linux/amd64 "$BASE_REF" >/dev/null
[ "$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$image_ref")" = linux/amd64 ] || fail "image is not linux/amd64"
[ "$(docker image inspect --format '{{index .Config.Labels "io.appbox.rutorrent.revision"}}' "$image_ref")" = "$RUTORRENT_REVISION" ] \
    || fail "ruTorrent revision label differs from $BASE_NAME"
[ "$(docker image inspect --format '{{index .Config.Labels "io.appbox.rutorrent.base-image"}}' "$image_ref")" = "$BASE_REF" ] \
    || fail "base-image label is not the $BASE_NAME digest"
[ "$(docker image inspect --format '{{index .Config.Labels "io.appbox.php85-artifact"}}' "$image_ref")" = \
  "$(docker image inspect --format '{{index .Config.Labels "io.appbox.php85-artifact"}}' "$BASE_REF")" ] \
    || fail "php85-artifact label differs from $BASE_NAME"
for field in '{{json .Config.Entrypoint}}' '{{json .Config.Cmd}}' '{{json .Config.Healthcheck}}' '{{json .Config.Env}}' '{{json .Config.User}}' '{{json .Config.ExposedPorts}}' '{{json .Config.Volumes}}' '{{json .Config.WorkingDir}}'; do
    [ "$(docker image inspect --format "$field" "$image_ref")" = "$(docker image inspect --format "$field" "$BASE_REF")" ] \
        || fail "image config $field differs from $BASE_NAME"
done
docker image inspect --format '{{range .RootFS.Layers}}{{println .}}{{end}}' "$BASE_REF" | sed '/^$/d' > "$work_dir/base-layers"
docker image inspect --format '{{range .RootFS.Layers}}{{println .}}{{end}}' "$image_ref" | sed '/^$/d' > "$work_dir/image-layers"
base_layer_count=$(wc -l < "$work_dir/base-layers")
extra_layers=$(( $(wc -l < "$work_dir/image-layers") - base_layer_count ))
head -n "$base_layer_count" "$work_dir/image-layers" | cmp -s - "$work_dir/base-layers" \
    || fail "image does not start with the $BASE_NAME layers"
[ "$extra_layers" -eq "$EXTRA_LAYERS" ] || fail "image adds $extra_layers layer(s) to $BASE_NAME; expected $EXTRA_LAYERS"
echo "$BASE_NAME layers ($base_layer_count) plus $extra_layers; labels, entrypoint, healthcheck and environment unchanged"

echo "== Filesystem: only the patch script and the generated stylesheets differ from $BASE_NAME"
# Every path's type, mode, owner and link target, and every regular file's
# SHA-256. Docker bind-mounts the three /etc files below per container.
fs_listing='find / -xdev \( -path /etc/hostname -o -path /etc/hosts -o -path /etc/resolv.conf \) -prune -o -printf "%y %m %u:%g %p -> %l\n" | sort; find / -xdev \( -path /etc/hostname -o -path /etc/hosts -o -path /etc/resolv.conf \) -prune -o -type f -exec sha256sum {} + | sort -k 2'
in_image "$BASE_REF" sh -c "$fs_listing" > "$work_dir/base-fs"
in_image "$image_ref" sh -c "$fs_listing" > "$work_dir/image-fs"
[ "$(wc -l < "$work_dir/image-fs")" -gt 10000 ] || fail "filesystem listing looks incomplete"
diff "$work_dir/base-fs" "$work_dir/image-fs" | sed -n 's/^> //p' | sort -k 2 > "$work_dir/fs-added" || true
diff "$work_dir/base-fs" "$work_dir/image-fs" | sed -n 's/^< //p' | sort -k 2 > "$work_dir/fs-removed" || true
# Expected stylesheets: the repository's script run on a copy of the 5.3.15.7 plugin.
docker run --rm --platform linux/amd64 --network none -v "$repo_dir/scripts:/gate-scripts:ro" --entrypoint sh "$BASE_REF" -c \
    "set -e; cp -a $PLUGIN /tmp/plugin; python3 /gate-scripts/patch-autodl-rutorrent-html5.py /tmp/plugin
     for t in $GENERATED; do sha256sum /tmp/plugin/css/\$t.min.css; done" \
    | sed "s#/tmp/plugin#$PLUGIN#" > "$work_dir/expected-css" || fail "could not run the repository script on the $BASE_NAME plugin"
[ "$(wc -l < "$work_dir/expected-css")" -eq 4 ] || fail "the repository script did not write four stylesheets"
script_sum=$(sha256sum "$repo_dir/scripts/patch-autodl-rutorrent-html5.py" | awk '{print $1}')
grep -qxF "$script_sum  $PATCH_SCRIPT" "$work_dir/image-fs" || fail "$PATCH_SCRIPT in the image is not scripts/patch-autodl-rutorrent-html5.py"
base_script_entry=$(grep -E "^f [0-7]+ [^ ]+ $PATCH_SCRIPT -> \$" "$work_dir/base-fs") || fail "$PATCH_SCRIPT missing from $BASE_NAME"
grep -qxF "$base_script_entry" "$work_dir/image-fs" || fail "$PATCH_SCRIPT mode or owner differs from $BASE_NAME"
{
    echo "$script_sum  $PATCH_SCRIPT"
    cat "$work_dir/expected-css"
    for t in $GENERATED; do echo "f 644 nobody:nogroup $PLUGIN/css/$t.min.css -> "; done
} | sort -k 2 > "$work_dir/fs-expected"
cmp -s "$work_dir/fs-added" "$work_dir/fs-expected" \
    || { diff "$work_dir/fs-expected" "$work_dir/fs-added" >&2 || true; fail "unexpected filesystem additions or changes"; }
[ "$(wc -l < "$work_dir/fs-removed")" -eq 1 ] && grep -q " $PATCH_SCRIPT\$" "$work_dir/fs-removed" \
    || { cat "$work_dir/fs-removed" >&2; fail "unexpected filesystem removals"; }
echo "$(wc -l < "$work_dir/image-fs") entries; only $PATCH_SCRIPT (identical to scripts/) and the four stylesheets (identical to the script's output, 0644 nobody:nogroup) differ"

echo "== Patch script"
in_image "$image_ref" python3 -c "import ast; ast.parse(open('$PATCH_SCRIPT').read())" || fail "patch script does not parse"
in_image "$image_ref" sh -c "set -e
    cp -a $PLUGIN /tmp/p
    cd /tmp/p && find . -type f -exec sha256sum {} + | sort > /tmp/before
    python3 $PATCH_SCRIPT /tmp/p
    cd /tmp/p && find . -type f -exec sha256sum {} + | sort > /tmp/after
    cmp /tmp/before /tmp/after
    printf '/* custom */\n' > /tmp/p/css/oblivionblue.min.css
    rm /tmp/p/css/darkbetter.min.css
    python3 $PATCH_SCRIPT /tmp/p
    test \"\$(cat /tmp/p/css/oblivionblue.min.css)\" = '/* custom */'
    cmp /tmp/p/css/darkbetter.min.css $PLUGIN/css/darkbetter.min.css
    rm -r /tmp/p/css
    python3 $PATCH_SCRIPT /tmp/p
    test ! -e /tmp/p/css" || fail "patch script is not idempotent, overwrote a foreign stylesheet or failed without a css directory"
echo "second run changes nothing; a stylesheet it did not write is kept; a deleted one comes back; no css directory is fine"

PASSWORD=$(od -An -N18 -tx1 /dev/urandom | tr -d ' \n')
RUTORRENT_PASSWORD=$PASSWORD
export PASSWORD RUTORRENT_PASSWORD

echo "== Fresh install, then restart"
new_volume "$run_id-fresh-torrents"
new_volume "$run_id-fresh-passwd"
start_app "$run_id-fresh" "$image_ref" "$run_id-fresh-torrents" "$run_id-fresh-passwd"
fresh_summary=$(runtime_check "$run_id-fresh" check "$PHP_VERSION") || fail "fresh install runtime checks failed"
echo "$fresh_summary" | tail -n 1
fresh_hash=$(echo "$fresh_summary" | tail -n 1 | jq -r '.addtorrent_upload')
step "fresh install login checks failed" auth_check "$run_id-fresh" login
step "fresh install stylesheets are not served" theme_check "$run_id-fresh"
docker restart --time 30 "$run_id-fresh" >/dev/null
wait_healthy "$run_id-fresh"; wait_rpc "$run_id-fresh"
step "login checks after restart failed" auth_check "$run_id-fresh" login
step "runtime checks after restart failed" runtime_check "$run_id-fresh" check "$PHP_VERSION" "$fresh_hash"
step "stylesheets are not served after restart" theme_check "$run_id-fresh"

echo "== Custom autodl-rutorrent plugin without the stylesheets"
# 03-config.sh copies /torrents/config/rutorrent/plugins/<plugin> over the
# image's copy and then runs the patch script on it. A custom stylesheet for
# one of the themes must survive; the other three must be generated.
docker exec "$run_id-fresh" sh -c "set -e
    cp -a $PLUGIN /torrents/config/rutorrent/plugins/autodl-rutorrent
    cd /torrents/config/rutorrent/plugins/autodl-rutorrent/css
    rm club-quickbox.min.css darkbetter.min.css materialdesign.min.css oblivionblue.min.css
    printf '/* custom */\n' > materialdesign.min.css
    chown -R rtorrent:rtorrent /torrents/config/rutorrent/plugins/autodl-rutorrent"
docker restart --time 30 "$run_id-fresh" >/dev/null
wait_healthy "$run_id-fresh"; wait_rpc "$run_id-fresh"
docker exec "$run_id-fresh" sh -c "set -e
    test \"\$(cat $PLUGIN/css/materialdesign.min.css)\" = '/* custom */'
    for t in club-quickbox darkbetter oblivionblue; do head -n 1 $PLUGIN/css/\$t.min.css | grep -q '^/\* Generated by Appbox'; done" \
    || fail "the custom plugin did not get the stylesheets, or its own stylesheet was replaced"
echo "custom plugin patched on start; its own materialdesign.min.css kept"
# A restart keeps the container's copy of the custom plugin; re-creating the
# container (as an Appbox update does) brings back the image's plugin.
docker exec "$run_id-fresh" rm -rf /torrents/config/rutorrent/plugins/autodl-rutorrent
docker rm -fv "$run_id-fresh" >/dev/null
start_app "$run_id-recreated" "$image_ref" "$run_id-fresh-torrents" "$run_id-fresh-passwd"
step "stylesheets are not served after removing the custom plugin and re-creating the container" theme_check "$run_id-recreated"
docker rm -fv "$run_id-recreated" >/dev/null

echo "== Upgrade from $BASE_NAME with the same /torrents and /passwd (club-QuickBox selected)"
new_volume "$run_id-up-torrents"
new_volume "$run_id-up-passwd"
start_app "$run_id-old" "$BASE_REF" "$run_id-up-torrents" "$run_id-up-passwd"
seeded=$(seed "$run_id-old") || fail "could not add a torrent on $BASE_NAME"
case "$seeded" in
    [0-9A-F][0-9A-F][0-9A-F][0-9A-F]*) ;;
    *) fail "unexpected seed hash: $seeded" ;;
esac
docker exec "$run_id-old" sh -c 'echo appbox-gate > /torrents/completed/appbox-gate-marker.txt && chown rtorrent:rtorrent /torrents/completed/appbox-gate-marker.txt'
printf '%s' "$THEME_DAT" | docker exec -i -u rtorrent "$run_id-old" sh -c 'cat > /torrents/config/rutorrent/share/users/releasegate/settings/theme.dat'
docker exec -u rtorrent "$run_id-old" sh -c 'for i in 1 2 3 4 5; do printf "\n[filter Gate filter %s]\nenabled = false\nmatch-releases = *gate%s*\n" "$i" "$i"; done >> /torrents/config/autodl/autodl.cfg'
status=$(docker exec -e USERNAME=releasegate -e PASSWORD "$run_id-old" python3 -c '
import base64, os, urllib.request, urllib.error
r = urllib.request.Request("http://127.0.0.1/plugins/autodl-rutorrent/css/club-quickbox.min.css")
r.add_header("Authorization", "Basic " + base64.b64encode((os.environ["USERNAME"] + ":" + os.environ["PASSWORD"]).encode()).decode())
try:
    print(urllib.request.urlopen(r, timeout=60).status)
except urllib.error.HTTPError as e:
    print(e.code)')
[ "$status" = 404 ] || fail "control: $BASE_NAME served club-quickbox.min.css (HTTP $status); the gate cannot show the fix"
echo "control: $BASE_NAME returns 404 for club-quickbox.min.css"
docker exec "$run_id-old" python3 -c 'import xmlrpc.client; xmlrpc.client.ServerProxy("http://127.0.0.1:8001/").session.save()'
volume_state "$run_id-old" > "$work_dir/state-old"
grep -q "^$seeded\.torrent\$" "$work_dir/state-old" || fail "seeded torrent missing from the $BASE_NAME session"
docker stop --time 30 "$run_id-old" >/dev/null
start_app "$run_id-new" "$image_ref" "$run_id-up-torrents" "$run_id-up-passwd"
volume_state "$run_id-new" > "$work_dir/state-new"
diff "$work_dir/state-old" "$work_dir/state-new" || fail "upgrade changed .rtorrent.rc, the session, completed data, theme.dat or autodl.cfg"
upgrade_summary=$(runtime_check "$run_id-new" check "$PHP_VERSION" "$seeded") || fail "upgrade runtime checks failed"
echo "$upgrade_summary" | tail -n 1
step "login checks after upgrade failed" auth_check "$run_id-new" login
step "stylesheets are not served after upgrade" theme_check "$run_id-new"
echo "upgrade kept .rtorrent.rc, the session torrents, completed data, the club-QuickBox selection and autodl.cfg"
docker rm -fv "$run_id-old" "$run_id-new" >/dev/null

check_registry

if [ "$gate_mode" = release ]; then
    echo "PASS: $image_ref"
else
    echo "TRIAL PASS: $image_ref; not a release approval"
fi
