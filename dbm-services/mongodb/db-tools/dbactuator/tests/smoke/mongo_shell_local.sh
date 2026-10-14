#!/usr/bin/env bash
# 本地冒烟：不启动 MongoDB。
# 1. 用临时目录里的假 mongod 确认主版本 >= 5 选出 mongosh，4.4 选出 mongo，8.0 目录可以没有 mongo。
# 2. 非 tlinux4 机器上确认不会执行 tos / dnf。
# 3. 如果本机已经装了 /usr/local/mongodb，再核对真实安装包里的客户端是否和主版本一致。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ -x /usr/local/go/bin/go ]]; then
  export PATH="/usr/local/go/bin:${PATH}"
fi

echo "==> local mongo shell smoke"
go test -count=1 -v ./pkg/common/ \
  -run 'TestMongoShellName|TestIsTlinux4Text|TestSmokeMongoShellLocal|TestSmokeTlinux4OpenSSLNoop'

echo "==> actuator atom jobs smoke"
go test -count=1 -v ./pkg/atomjobs/atommongodb/ \
  -run 'TestSmokeActuatorTasksUseMongosh|TestSmokeInstanceOpUsesMongosh|TestSmokeInstallTasksPrepareTlinux4Dependency'

if [[ -x /usr/local/mongodb/bin/mongod ]]; then
  ver="$(/usr/local/mongodb/bin/mongod -version 2>/dev/null | awk '/db version/{print $3}' | sed 's/^v//' | head -n 1)"
  major="${ver%%.*}"
  echo "==> installed mongod ${ver}"
  if [[ -n "${major}" && "${major}" -ge 5 ]]; then
    if [[ ! -x /usr/local/mongodb/bin/mongosh ]]; then
      echo "ERROR: mongod ${ver} requires mongosh, binary missing" >&2
      exit 1
    fi
    echo "installed client: mongosh"
  else
    if [[ ! -x /usr/local/mongodb/bin/mongo ]]; then
      echo "ERROR: mongod ${ver} requires mongo shell, binary missing" >&2
      exit 1
    fi
    echo "installed client: mongo"
  fi
else
  echo "==> /usr/local/mongodb/bin/mongod not installed, skip real package check"
fi

echo "==> smoke ok"
