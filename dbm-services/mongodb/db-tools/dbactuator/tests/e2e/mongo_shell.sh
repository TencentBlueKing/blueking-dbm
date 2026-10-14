#!/usr/bin/env bash
# 与 actuator ResolveMongoShellBin 一致：优先 mongosh，没有则用 mongo。

mongo_shell_bin() {
  if [[ -x "${BIN_DIR}/mongodb/bin/mongosh" ]]; then
    echo "${BIN_DIR}/mongodb/bin/mongosh"
  else
    echo "${BIN_DIR}/mongodb/bin/mongo"
  fi
}
