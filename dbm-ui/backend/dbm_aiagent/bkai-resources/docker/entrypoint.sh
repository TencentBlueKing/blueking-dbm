#!/usr/bin/env bash
# dbm-aidev-init: render mcps → validate → sync
#
# Job 必填: BK_APIGW_STAGE_NAME
# Job 可选: BK_APIGW_MCP_NAME (默认 bkdbm-mcp), BKAI_SPACE (默认 system-bkaidev)
set -euo pipefail

PKG=/app/bkai-resources
GATEWAY="${BK_APIGW_MCP_NAME:-bkdbm-mcp}"
STAGE="${BK_APIGW_STAGE_NAME:?BK_APIGW_STAGE_NAME is required}"
SPACE="${BKAI_SPACE:-system-bkaidev}"

echo "[dbm-aidev-init] gateway=${GATEWAY} stage=${STAGE} space=${SPACE}"

python3 "${PKG}/docker/render_agent_configs.py" \
  --package "${PKG}" \
  --bindings "${PKG}/docker/mcp_bindings.json" \
  --gateway "${GATEWAY}" \
  --stage "${STAGE}"

bkai-cli validate -f "${PKG}/bkai.yaml"
bkai-cli sync -f "${PKG}/bkai.yaml" --space "${SPACE}"

echo "[dbm-aidev-init] done"
