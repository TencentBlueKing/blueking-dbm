#!/bin/sh

export APP_ID="bk-dbm"
export APP_TOKEN="xxxxxx"
export DJANGO_SETTINGS_MODULE=config.prod
export BK_LOG_DIR=/tmp/bk-dbm
export BK_IAM_SKIP=true

export BKREPO_USERNAME="bkdbm"
export BKREPO_PASSWORD="bkdbm"
export BKREPO_PROJECT="blueking"
export BKREPO_PUBLIC_BUCKET="bkdbm"
export BKREPO_ENDPOINT_URL="http://bkrepo.example.com"