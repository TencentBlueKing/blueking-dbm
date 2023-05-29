#!/usr/bin/env bash

# 安全模式
set -euo pipefail 

# 重置PATH
PATH=/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

# 通用脚本框架变量
PROGRAM=$(basename "$0")
EXITCODE=0

BKREPO_USER=
BKREPO_PASSWORD=
BKREPO_API=http://127.0.0.1:8080
BKREPO_PROJECT=generic # 项目代号
BKREPO_NAME=bk-dbm     # 仓库名字，默认自定义仓库
DOWNLOAD_DIR=/tmp       # 下载文件的默认路径：/tmp
BKREPO_METHOD=GET       # 默认为下载
BKREPO_PUT_OVERWRITE=true   # 上传时是否覆盖仓库
REMOTE_PATH=
declare -a REMOTE_FILE=()   # 下载的文件列表
declare -a UPLOAD_FILE=()   # 上传的文件列表

trap 'rm -f /tmp/bkrepo_tool.*.log' EXIT
usage () {
    cat <<EOF
用法: 
    $PROGRAM -u <bkrepo_user> -p <bkrepo_password> [ -d <download_dir> ] -r /devops/path1 -r /devops/path2 ...
    $PROGRAM -u <bkrepo_user> -p <bkrepo_password> -X PUT -T local_file_path1 -T local_file_path2 -R remote_path
            [ -u, --user        [必填] "指定访问bkrepo的api用户名" ]
            [ -p, --password    [必填] "指定访问bkrepo的api密码" ] 
            [ -i, --url         [必填] "指定访问bkrepo的url，默认是$BKREPO_API" ] 
            [ -r, --remote-file [必填] "指定下载的远程文件路径路径" ]
            [ -n, --repo        [选填] "指定项目的仓库名字，默认为$BKREPO_NAME" ] 
            [ -P, --project     [选填] "指定项目名字，默认为blueking" ] 
            [ -d, --dir         [选填] "指定下载制品库文件的存放文件夹，若不指定，则为/tmp" ]
            [ -X, --method      [选填] "默认为下载（GET），可选PUT，为上传" ]

            -X PUT时，以下参数生效:
                [ -T, --upload-file [必填] "指定需要上传的本机文件路径" ]
                [ -R, --remote-path [必填] "指定上传到的仓库目录的路径" ]
                [ -O, --override [选填] "指定上传同名文件是否覆盖" ]
            [ -h --help -?      查看帮助 ]
EOF
}

usage_and_exit () {
    usage
    exit "$1"
}

log () {
    echo "$@"
}

error () {
    echo "$@" 1>&2
    usage_and_exit 1
}

warning () {
    echo "$@" 1>&2
    EXITCODE=$((EXITCODE + 1))
}

# 解析命令行参数，长短混合模式
(( $# == 0 )) && usage_and_exit 1
while (( $# > 0 )); do 
    case "$1" in
        -u | --user )
            shift
            BKREPO_USER=$1
            ;;
        -p | --password)
            shift
            BKREPO_PASSWORD=$1
            ;;
        -i | --url)
            shift
            BKREPO_API=$1
            ;;
        -d | --dir )
            shift
            DOWNLOAD_DIR=$1
            ;;
        -n | --name )
            shift
            BKREPO_NAME=$1
            ;;
        -P | --project )
            shift
            BKREPO_PROJECT=$1
            ;;
        -r | --remote-file )
            shift
            REMOTE_FILE+=("$1")
            ;;
        -T | --upload-file )
            shift
            UPLOAD_FILE+=("$1")
            ;;
        -O | --override)
            BKREPO_PUT_OVERWRITE=true
            ;;
        -R | --remote-path )
            shift
            REMOTE_PATH=$1
            ;;
        -X | --method )
            shift
            BKREPO_METHOD=$1
            ;;
        --help | -h | '-?' )
            usage_and_exit 0
            ;;
        -*)
            error "不可识别的参数: $1"
            ;;
        *) 
            break
            ;;
    esac
    shift 
done 

if [[ -z "$BKREPO_USER" || -z "$BKREPO_PASSWORD" ]]; then
    warning "-u, -p must not be empty"
fi

if (( EXITCODE > 0 )); then
    usage_and_exit "$EXITCODE"
fi

case $BKREPO_METHOD in
    GET ) 
        if ! [[ -d "$DOWNLOAD_DIR" ]]; then
            mkdir -p "$DOWNLOAD_DIR"
        fi

        cd "$DOWNLOAD_DIR" || { echo "can't change into $DOWNLOAD_DIR"; exit 1; }

        for remote_file in "${REMOTE_FILE[@]}"; do
            echo "start downloading $remote_file ..."
            curl -X "$BKREPO_METHOD" -sLO -u "$BKREPO_USER:$BKREPO_PASSWORD" "${BKREPO_API}/${BKREPO_PROJECT}/$BKREPO_NAME/$remote_file"
            rt=$?
            if [[ $rt -eq 0 ]]; then
                echo "download $remote_file finished in $DOWNLOAD_DIR/${remote_file##*/}"
            else
                echo "download $remote_file with error code: <$rt>"
            fi
        done
        ;;
    PUT )
        for local_file in "${UPLOAD_FILE[@]}"; do
            if [[ -r "$local_file" ]]; then
                local_file_md5=$(md5sum "$local_file" | awk '{print $1}')
                local_file_name=$(basename "$local_file")
                http_code=$(curl -s -o /tmp/bkrepo_tool.$$.log -w "%{http_code}" \
                    -u "$BKREPO_USER:$BKREPO_PASSWORD" "${BKREPO_API}/${BKREPO_PROJECT}/${BKREPO_NAME}/$REMOTE_PATH/$local_file_name" \
                    -T "$local_file" \
                    -H "X-BKREPO-OVERWRITE: $BKREPO_PUT_OVERWRITE" \
                    -H "X-BKREPO-MD5: $local_file_md5"
                )
                if [[ $http_code -eq 200 ]]; then
                    echo "upload $local_file to $REMOTE_PATH succeed"
                else
                    echo "upload $local_file to $REMOTE_PATH failed"
                    echo "http response is: $(</tmp/bkrepo_tool.$$.log)"
                fi
            else
                echo "$local_file doesn't exits"
            fi
        done
        ;;
    *)
        echo "unknown method: $BKREPO_METHOD"
        usage_and_exit 2
        ;;
esac
 
