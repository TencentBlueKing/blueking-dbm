#!/bin/bash

function echo_step() {
    echo -e '\033[0;32m'"$1"'\033[0m'
}

function log_info() {
    NOW=$(date +"%Y-%m-%d %H:%M:%S")
    echo "${NOW} [INFO] $1"
}

function log_error() {
    NOW=$(date +"%Y-%m-%d %H:%M:%S")
    echo "${NOW} [ERROR] $1"
}


function if_error_then_exit() {
    if [ "$1" -ne 0 ]
    then
        log_error "$2"
        exit 1
    fi
}



echo_step "add js header"
JS_HOME_DIRS=$(find . -name "js" -type d  | grep -v asset | grep -v node_modules | grep -v admin)
for JS_DIR in ${JS_HOME_DIRS}
do
    JS_FILES=$(find $JS_DIR -name "*.js" -not -name "*.min.js")
    for JS_FILE in ${JS_FILES}
    do
        LINE_C=$(head -5 "${JS_FILE}")
        LINE_H=$(head -5 tmp/LICENSE_JSCSS_HEADER.txt)

        if [ "${LINE_C}" != "${LINE_H}" ]
        then
            echo "${JS_FILE} without license header, add"
            cat tmp/LICENSE_JSCSS_HEADER.txt "${JS_FILE}" > t.js && mv t.js "${JS_FILE}" && echo "add header to ${JS_FILE}"
            if_error_then_exit $? "add header to js fail"
        fi

    done
done

echo_step "add css header"
CSS_HOME_DIRS=$(find . -name "css" -type d  | grep -v asset | grep -v node_modules | grep -v admin)
for CSS_DIR in ${CSS_HOME_DIRS}
do
    # NOTE: do gulp first!!!!!!!!! will add license to min.css too
    # CSS_FILES=$(find $CSS_DIR -name "*.css" -not -name "*.min.css")
    CSS_FILES=$(find $CSS_DIR -name "*.css")
    for CSS_FILE in ${CSS_FILES}
    do

        LINE_C=$(head -5 "${CSS_FILE}")
        LINE_H=$(head -5 tmp/LICENSE_JSCSS_HEADER.txt)

        if [ "${LINE_C}" != "${LINE_H}" ]
        then
            echo "${CSS_FILE} without license header, add"
            cat tmp/LICENSE_JSCSS_HEADER.txt "${CSS_FILE}" > t.js && mv t.js "${CSS_FILE}" && echo "add header to ${CSS_FILE}"
            if_error_then_exit $? "add header to css fail"
        fi

    done
done
