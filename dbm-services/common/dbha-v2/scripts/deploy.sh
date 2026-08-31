#!/usr/bin/env bash
set -euo pipefail

#---------------------------------------------------------------
# Constants
#---------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

readonly SERVICES=(admin receiver analysis)
readonly PROBE=probe
readonly MODULE_SERVER=server
readonly MODULE_PROBE=probe

readonly SERVER_BIN_FILES=(
    dbha-admin
    dbha-analysis
    dbha-receiver
)

readonly PROBE_BIN_FILES=(
    dbha-probe
)

readonly TOOLKIT_FILES=(
    dbha-cluster
    dbha-bwmgr
)

readonly SERVER_SCRIPT_FILES=(
    setup.sh
    start-server.sh
    stop-server.sh
    deploy.sh
    render_configs.py
)

readonly PROBE_SCRIPT_FILES=(
    start-probe.sh
    start-probe-keepalive.sh
    stop-probe-keepalive.sh
    stop-probe.sh
    deploy.sh
    render_configs.py
    compare_probe_config.py
)

readonly SERVER_CONF_FILES=(
    admin.yaml
    analysis.yaml
    receiver.yaml
    cluster.yaml
    bwmgr.yaml
)

readonly PROBE_CONF_FILES=(
    probe.yaml
)

#---------------------------------------------------------------
# Helpers
#---------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
error() { echo "[ERROR] $*" >&2; exit 1; }

usage() {
    cat <<'USAGE'
Usage: deploy.sh -m <mode> -r <module> -s <source> -t <target> [options]

Modes:
  install   Full installation (binaries + configs + scripts + toolkits + lib)
  update    Update binaries + toolkits + scripts + lib (configs skipped)

Modules:
  server    Install/update server-side modules (admin/receiver/analysis)
  probe     Install/update probe module only

Required:
  -m <mode>     Deployment mode: install | update
  -r <module>   Module type: server | probe
  -s <source>   Source directory (package layout)
  -t <target>   Target deployment directory

Options:
  --no-restart  Skip stopping/starting services (update only)
  -y            Skip confirmation prompts
  -h, --help    Show this help message

Examples:
  # Fresh install (server side)
  deploy.sh -m install -r server -s /tmp/dbha-v2 -t /usr/local/dbha-v2

  # Fresh install (probe side)
  deploy.sh -m install -r probe -s /tmp/dbha-v2 -t /usr/local/dbha-v2

  # Update binaries and scripts only (server side)
  deploy.sh -m update -r server -s /tmp/dbha-v2 -t /usr/local/dbha-v2

  # Update without restarting services (probe side)
  deploy.sh -m update -r probe -s /tmp/dbha-v2 -t /usr/local/dbha-v2 \
      --no-restart
USAGE
    exit 0
}

confirm() {
    local msg="$1"
    if [ "${AUTO_YES}" -eq 1 ]; then
        return 0
    fi
    read -rp "${msg} [y/N]: " ans
    case "${ans}" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

#---------------------------------------------------------------
# Validation
#---------------------------------------------------------------
validate_module() {
    local module="$1"
    case "${module}" in
        "${MODULE_SERVER}"|"${MODULE_PROBE}") ;;
        *)
            error "invalid module: ${module} (must be server or probe)"
            ;;
    esac
}

validate_source() {
    local src="$1" module="$2"
    [ -d "${src}" ] \
        || error "source directory does not exist: ${src}"
    [ -d "${src}/bin" ] \
        || error "source missing bin/ directory: ${src}/bin"

    local module_bins=()
    if [ "${module}" = "${MODULE_SERVER}" ]; then
        module_bins=("${SERVER_BIN_FILES[@]}")
    else
        module_bins=("${PROBE_BIN_FILES[@]}")
    fi

    local missing=()
    for f in "${module_bins[@]}"; do
        [ -f "${src}/bin/${f}" ] || missing+=("bin/${f}")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        error "source missing binaries: ${missing[*]}"
    fi

    if [ ! -f "${src}/lib/guard-utils.sh" ]; then
        error "source missing required lib script: lib/guard-utils.sh"
    fi

    if [ "${module}" = "${MODULE_SERVER}" ]; then
        local missing_toolkits=()
        for f in "${TOOLKIT_FILES[@]}"; do
            [ -f "${src}/toolkits/${f}" ] || missing_toolkits+=("toolkits/${f}")
        done
        if [ ${#missing_toolkits[@]} -gt 0 ]; then
            error "source missing toolkits: ${missing_toolkits[*]}"
        fi
    fi
}

validate_target_for_update() {
    local tgt="$1"
    [ -d "${tgt}" ] \
        || error "target directory does not exist: ${tgt}"
    [ -d "${tgt}/bin" ] \
        || error "target missing bin/, is this a valid " \
                 "dbha-v2 installation? ${tgt}"
    [ -d "${tgt}/etc" ] \
        || error "target missing etc/, is this a valid " \
                 "dbha-v2 installation? ${tgt}"
}

#---------------------------------------------------------------
# Service management
#---------------------------------------------------------------
stop_services() {
    local tgt="$1" module="$2"
    info "stopping services ..."

    if [ "${module}" = "${MODULE_SERVER}" ]; then
        for svc in "${SERVICES[@]}"; do
            if [ -x "${tgt}/bin/dbha-${svc}" ]; then
                info "stopping dbha-${svc} ..."
                "${tgt}/bin/dbha-${svc}" stop \
                    -c "${tgt}/etc/${svc}.yaml" 2>/dev/null \
                    && info "dbha-${svc} stopped" \
                    || warn "dbha-${svc} stop returned non-zero"
            fi
        done
        return 0
    fi

    if [ -x "${tgt}/bin/dbha-${MODULE_PROBE}" ]; then
        info "stopping dbha-${PROBE} ..."
        "${tgt}/bin/dbha-${MODULE_PROBE}" stop \
            -c "${tgt}/etc/${MODULE_PROBE}.yaml" 2>/dev/null \
            && info "dbha-${MODULE_PROBE} stopped" \
            || warn "dbha-${MODULE_PROBE} stop returned non-zero"
    fi
}

start_services() {
    local tgt="$1" module="$2"
    info "starting services ..."

    if [ "${module}" = "${MODULE_SERVER}" ]; then
        for svc in "${SERVICES[@]}"; do
            if [ -x "${tgt}/bin/dbha-${svc}" ] \
                && [ -f "${tgt}/etc/${svc}.yaml" ]; then
                info "starting dbha-${svc} ..."
                "${tgt}/bin/dbha-${svc}" daemon-start \
                    -c "${tgt}/etc/${svc}.yaml" \
                    && info "dbha-${svc} started" \
                    || warn "dbha-${svc} start returned non-zero"
            fi
        done
        return 0
    fi

    if [ -x "${tgt}/bin/dbha-${MODULE_PROBE}" ] \
        && [ -f "${tgt}/etc/${MODULE_PROBE}.yaml" ]; then
        info "starting dbha-${PROBE} ..."
        "${tgt}/bin/dbha-${MODULE_PROBE}" daemon-start \
            -c "${tgt}/etc/${MODULE_PROBE}.yaml" \
            && info "dbha-${MODULE_PROBE} started" \
            || warn "dbha-${MODULE_PROBE} start returned non-zero"
    fi
}

#---------------------------------------------------------------
# Backup
#---------------------------------------------------------------
backup_dir() {
    local tgt="$1" sub="$2"
    local ts
    ts="$(date +%Y%m%d%H%M%S)"
    local bak="${tgt}/backup/${ts}/${sub}"
    if [ -d "${tgt}/${sub}" ]; then
        mkdir -p "${bak}"
        cp -a "${tgt}/${sub}/." "${bak}/"
        info "backed up ${sub}/ -> backup/${ts}/${sub}/"
    fi
}

#---------------------------------------------------------------
# Deploy helpers
#---------------------------------------------------------------
deploy_binaries() {
    local src="$1" tgt="$2" module="$3"
    info "deploying binaries ..."
    mkdir -p "${tgt}/bin"

    local module_bins=()
    if [ "${module}" = "${MODULE_SERVER}" ]; then
        module_bins=("${SERVER_BIN_FILES[@]}")
    else
        module_bins=("${PROBE_BIN_FILES[@]}")
    fi

    for f in "${module_bins[@]}"; do
        cp -f "${src}/bin/${f}" "${tgt}/bin/${f}"
        chmod +x "${tgt}/bin/${f}"
    done
    info "binaries deployed to ${tgt}/bin/"
}

deploy_toolkits() {
    local src="$1" tgt="$2" module="$3"
    if [ "${module}" != "${MODULE_SERVER}" ]; then
        info "probe module selected, skip toolkits deployment"
        return 0
    fi
    if [ ! -d "${src}/toolkits" ]; then
        warn "source has no toolkits/ directory, skipping"
        return 0
    fi
    info "deploying toolkits ..."
    mkdir -p "${tgt}/toolkits"
    for f in "${TOOLKIT_FILES[@]}"; do
        if [ -f "${src}/toolkits/${f}" ]; then
            cp -f "${src}/toolkits/${f}" "${tgt}/toolkits/${f}"
            chmod +x "${tgt}/toolkits/${f}"
        fi
    done
    info "toolkits deployed to ${tgt}/toolkits/"
}

deploy_scripts() {
    local src="$1" tgt="$2" module="$3"
    info "deploying scripts ..."

    local module_scripts=()
    if [ "${module}" = "${MODULE_SERVER}" ]; then
        module_scripts=("${SERVER_SCRIPT_FILES[@]}")
    else
        module_scripts=("${PROBE_SCRIPT_FILES[@]}")
    fi

    for f in "${module_scripts[@]}"; do
        if [ -f "${src}/${f}" ]; then
            cp -f "${src}/${f}" "${tgt}/${f}"
            chmod +x "${tgt}/${f}"
        fi
    done
    info "scripts deployed to ${tgt}/"
}

deploy_lib() {
    local src="$1" tgt="$2"
    if [ ! -d "${src}/lib" ]; then
        error "source missing lib/ directory: ${src}/lib"
    fi

    local lib_files lib_scripts target_scripts
    shopt -s nullglob
    lib_files=("${src}/lib/"*)
    lib_scripts=("${src}/lib/"*.sh)
    shopt -u nullglob

    if [ ${#lib_files[@]} -eq 0 ]; then
        error "source lib directory is empty: ${src}/lib"
    fi
    if [ ${#lib_scripts[@]} -eq 0 ]; then
        error "source lib directory missing shell scripts: ${src}/lib"
    fi

    info "deploying lib files ..."
    mkdir -p "${tgt}/lib"
    cp -f "${lib_files[@]}" "${tgt}/lib/"

    shopt -s nullglob
    target_scripts=("${tgt}/lib/"*.sh)
    shopt -u nullglob
    if [ ${#target_scripts[@]} -gt 0 ]; then
        chmod +x "${target_scripts[@]}"
    fi

    info "lib files deployed to ${tgt}/lib/"
}

deploy_configs() {
    local src="$1" tgt="$2" module="$3"
    if [ ! -d "${src}/etc" ]; then
        warn "source has no etc/ directory, skipping configs"
        return 0
    fi
    info "deploying configuration files ..."
    mkdir -p "${tgt}/etc"

    local module_configs=()
    if [ "${module}" = "${MODULE_SERVER}" ]; then
        module_configs=("${SERVER_CONF_FILES[@]}")
    else
        module_configs=("${PROBE_CONF_FILES[@]}")
    fi

    for f in "${module_configs[@]}"; do
        if [ -f "${src}/etc/${f}" ]; then
            if [ -f "${tgt}/etc/${f}" ]; then
                if ! confirm \
                    "  config ${f} already exists, overwrite?";
                then
                    info "skipping ${f}"
                    continue
                fi
            fi
            cp -f "${src}/etc/${f}" "${tgt}/etc/${f}"
        fi
    done
    info "configs deployed to ${tgt}/etc/"
}

#---------------------------------------------------------------
# Mode: install
#---------------------------------------------------------------
do_install() {
    local src="$1" tgt="$2" module="$3"

    info "=== INSTALL mode ==="
    info "module: ${module}"
    info "source: ${src}"
    info "target: ${tgt}"

    if [ -d "${tgt}/bin" ]; then
        warn "target already contains bin/ directory"
        if ! confirm \
            "  target may be an existing installation, continue?";
        then
            info "aborted"
            exit 0
        fi
    fi

    mkdir -p "${tgt}"
    deploy_binaries "${src}" "${tgt}" "${module}"
    deploy_toolkits "${src}" "${tgt}" "${module}"
    deploy_scripts  "${src}" "${tgt}" "${module}"
    deploy_lib      "${src}" "${tgt}"
    deploy_configs  "${src}" "${tgt}" "${module}"

    echo ""
    info "=== installation complete ==="
    info "target: ${tgt}"
    info ""
    info "next steps:"
    if [ "${module}" = "${MODULE_SERVER}" ]; then
        info "  1. configure: cd ${tgt} && ./setup.sh"
        info "  2. start server: ./start-server.sh"
        info "  3. if probe runs on other hosts, set in server rc:"
        info "     PROBE_INSTALL_DIR=<probe install directory>"
        info "     ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD='cd <probe install directory> && ./bin/dbha-probe health -j'"
        info "  4. toolkits: ./toolkits/dbha-cluster -c ./etc/cluster.yaml"
        info "             ./toolkits/dbha-bwmgr -c ./etc/bwmgr.yaml"
    else
        info "  1. configure probe config: edit ${tgt}/etc/probe.yaml"
        info "  2. start probe: ./start-probe.sh"
        info "  3. ensure server analysis rc uses probe install path: ${tgt}"
    fi
}

#---------------------------------------------------------------
# Mode: update
#---------------------------------------------------------------
do_update() {
    local src="$1" tgt="$2" module="$3" restart="$4"

    info "=== UPDATE mode ==="
    info "module: ${module}"
    info "source: ${src}"
    info "target: ${tgt}"
    info "restart services: ${restart}"
    echo ""

    if ! confirm "  proceed with update?"; then
        info "aborted"
        exit 0
    fi

    if [ "${restart}" = "yes" ]; then
        stop_services "${tgt}" "${module}"
    fi

    backup_dir "${tgt}" "bin"
    if [ "${module}" = "${MODULE_SERVER}" ]; then
        backup_dir "${tgt}" "toolkits"
    fi

    deploy_binaries "${src}" "${tgt}" "${module}"
    deploy_toolkits "${src}" "${tgt}" "${module}"
    deploy_scripts  "${src}" "${tgt}" "${module}"
    deploy_lib      "${src}" "${tgt}"

    if [ "${restart}" = "yes" ]; then
        start_services "${tgt}" "${module}"
    fi

    echo ""
    info "=== update complete ==="
    info "target: ${tgt}"
    if [ "${module}" = "${MODULE_SERVER}" ]; then
        info "if probe runs on other hosts, ensure server rc has:"
        info "  PROBE_INSTALL_DIR=<probe install directory>"
        info "  ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD='cd <probe install directory> && ./bin/dbha-probe health -j'"
        info "toolkit binaries updated; etc/cluster.yaml and etc/bwmgr.yaml are not changed by update"
    else
        info "ensure server analysis rc uses probe install path: ${tgt}"
    fi
    if [ "${restart}" != "yes" ]; then
        info "services were NOT restarted (--no-restart)"
        info "restart manually when ready:"
        if [ "${module}" = "${MODULE_SERVER}" ]; then
            info "  cd ${tgt} && ./start-server.sh"
        else
            info "  cd ${tgt} && ./start-probe.sh"
        fi
    fi
}

#---------------------------------------------------------------
# Argument parsing
#---------------------------------------------------------------
MODE=""
MODULE=""
SOURCE=""
TARGET=""
RESTART="yes"
AUTO_YES=0

while [ $# -gt 0 ]; do
    case "$1" in
        -m)
            MODE="$2"; shift 2 ;;
        -r|--module)
            MODULE="$2"; shift 2 ;;
        -s)
            SOURCE="$2"; shift 2 ;;
        -t)
            TARGET="$2"; shift 2 ;;
        --no-restart)
            RESTART="no"; shift ;;
        -y)
            AUTO_YES=1; shift ;;
        -h|--help)
            usage ;;
        *)
            error "unknown argument: $1" ;;
    esac
done

[ -n "${MODE}" ]   || error "missing required option: -m <mode>"
[ -n "${MODULE}" ] || error "missing required option: -r <module>"
[ -n "${SOURCE}" ] || error "missing required option: -s <source>"
[ -n "${TARGET}" ] || error "missing required option: -t <target>"

SOURCE="$(cd "${SOURCE}" && pwd)"
validate_module "${MODULE}"

case "${MODE}" in
    install)
        validate_source "${SOURCE}" "${MODULE}"
        do_install "${SOURCE}" "${TARGET}" "${MODULE}"
        ;;
    update)
        validate_source "${SOURCE}" "${MODULE}"
        validate_target_for_update "${TARGET}"
        do_update "${SOURCE}" "${TARGET}" "${MODULE}" "${RESTART}"
        ;;
    *)
        error "invalid mode: ${MODE} (must be install or update)"
        ;;
esac
