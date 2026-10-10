#!/usr/bin/env bash
# dbm-aidev-init: render mcps → bkai-init validate → sync
#
# Job 必填: BK_APIGW_STAGE_NAME, BKAI_SPACE（目标空间 ID）, BKAI_SKILL_IMAGE_REPO（仓库地址，不带末尾 /）
# Job 可选:
#   BK_APIGW_MCP_NAME   (默认 bkdbm-mcp)
#   BKAI_TENANT_ID      (默认 system)
#   BKAI_PUBLISH        (默认 1，传 0 则只同步草稿)
#   BKAI_PUBLISH_CONFIG_ONLY (默认 1)
#   BKAI_ADMINS              (可选，空格分隔的 bk_username，追加 Agent 管理员)
set -euo pipefail

PKG=/app/bkai-resources
GATEWAY="${BK_APIGW_MCP_NAME:-bkdbm-mcp}"
STAGE="${BK_APIGW_STAGE_NAME:?BK_APIGW_STAGE_NAME is required}"
SPACE="${BKAI_SPACE:?BKAI_SPACE (space id) is required}"
SKILL_IMAGE_REPO="${BKAI_SKILL_IMAGE_REPO:?BKAI_SKILL_IMAGE_REPO is required}"
TENANT_ID="${BKAI_TENANT_ID:-system}"
PUBLISH="${BKAI_PUBLISH:-1}"
PUBLISH_CONFIG_ONLY="${BKAI_PUBLISH_CONFIG_ONLY:-1}"

echo "[dbm-aidev-init] gateway=${GATEWAY} stage=${STAGE} tenant=${TENANT_ID} space=${SPACE} publish=${PUBLISH}"

python3 "${PKG}/docker/render_agent_configs.py" \
  --package "${PKG}" \
  --bindings "${PKG}/docker/mcp_bindings.json" \
  --gateway "${GATEWAY}" \
  --stage "${STAGE}"

SYNC_ARGS=(
  -f "${PKG}/bkai.yaml"
  --tenant-id "${TENANT_ID}"
  --space "${SPACE}"
  --confirm
)

if [[ "${PUBLISH}" == "1" ]]; then
  SYNC_ARGS+=(--publish "--publish_config_only=${PUBLISH_CONFIG_ONLY}")
fi

if [[ -n "${BKAI_ADMINS:-}" ]]; then
  read -r -a ADMINS <<< "${BKAI_ADMINS}"
  SYNC_ARGS+=(--admins "${ADMINS[@]}")
fi

SYNC_ARGS+=(--var "BKAI_SKILL_IMAGE_REPO=${SKILL_IMAGE_REPO}")

bkai-init validate -f "${PKG}/bkai.yaml" --space "${SPACE}" \
  --var "BKAI_SKILL_IMAGE_REPO=${SKILL_IMAGE_REPO}"
bkai-init sync "${SYNC_ARGS[@]}"

echo "[dbm-aidev-init] done"
