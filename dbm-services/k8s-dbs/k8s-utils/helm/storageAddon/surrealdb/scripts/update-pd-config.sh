#!/bin/sh
# this image does not have bash..

set -ex

config="${1:?missing config}"
value="${2:?missing value}"

/kb-tools/pd-ctl config set "$config" "$value"
