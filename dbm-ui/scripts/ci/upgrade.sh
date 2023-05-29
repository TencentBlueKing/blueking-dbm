#!/bin/bash
# 更新脚本

# 安全模式
set -euo pipefail

usage () {
    echo "usage: upgrade MODULE VERSION"
    echo "MODULE: dbm|dbconfig|dbpriv|db-simulation|db-resource|db-remote-service|db-dns-api|hadb-api|grafana"
}

usage_and_exit() {
    usage
    exit "$1"
}

(($# != 2)) && usage_and_exit 1

MODULE=$1
NEW_VERSION=$2
NAMESPACE=${NAMESPACE:-blueking}
VERSION_FILE="environments/default/version.yaml"
DBM_CUSTOM_FILE="environments/default/bkdbm-custom-values.yaml.gotmpl"
TIME_STAMP=$(date +%Y-%m-%d\ %H:%M:%S)
BK_DOMAIN=$(yq e '.domain.bkDomain' environments/default/custom.yaml)

log (){
   local level=INFO
   echo -e "$TIME_STAMP [${level}] \033[44;37m $@ \033[0m"
}

fail () {
    local level=ERROR
    echo -e "$TIME_STAMP [${level}] \033[31m $@ \033[0m"
    exit 1
}

notice () {

    local namespace release_name

    namespace=$1
    release_name=$2

    update_status="$(helm history -n "$namespace" "$release_name" | tail -n1)"

    curl 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=6a752425-df8c-4388-93ce-81eca5cf543b' \
    -H 'Content-Type: application/json' \
    -d '
    {
        "msgtype": "markdown",
        "markdown": {
            "content": "['"http://$BK_DOMAIN"']('"http://$BK_DOMAIN"')\n
            ><font color=\"comment\">'"$update_status"'</font>"
         }
    }'
}

map_module_name (){
    local module_name=$1

    case $module_name in
        bk-repo) module_name=bkrepo ;;
        bk-auth) module_name=bkauth ;;
        bk-iam) module_name=bkiam ;;
        bk-iam-saas) module_name=bkiam-saas ;;
        bk-iam-search-engine) module_name=bkiam-search-engine ;;
        bk-ssm) module_name=bkssm ;;
        bk-paas) module_name=bkpaas3 ;;

        *) module_name=$module_name ;;
    esac
    echo "$module_name"

}

upgrade () {
    local module=$1
    local module_name old_version version
    version=$2

    cd /root/bkhelmfile/blueking

    log "update blueking repo"
    helm repo update

    log "begining update $MODULE"
    if [[ $module == "bk-dbm" ]]; then
        module_name=$(map_module_name "$module")
        old_version=$(awk '{print $2}' <<<$(grep $module_name $VERSION_FILE))

        log "update version file"
        sed -i "/${module_name}/s/$old_version/\"$version\"/g" $VERSION_FILE

        helmfile -f 05-bkdbm.yaml.gotmpl sync
    else
        yq e -i ".${module}.image.tag=\"$version\"" $DBM_CUSTOM_FILE
        # yq e -i ".${module}.image.appVersion=\"\"" $DBM_CUSTOM_FILE
        helmfile -f 05-bkdbm.yaml.gotmpl sync
        kubectl get pods -l app.kubernetes.io/instance=bk-dbm
    fi
    notice blueking "$module" > /dev/null 2>&1
}

case "$MODULE" in
    dbm|dbconfig|dbpriv|db-simulation|db-resource|db-remote-service|db-dns-api|hadb-api|grafana)
        upgrade "$MODULE" "$NEW_VERSION"
        ;;
    bk-dbm)
        upgrade "$MODULE" "$NEW_VERSION"
        ;;
    -h|--help)
        usage; exit 0
        ;;
    *)
        usage
        exit 0
        ;;
esac
