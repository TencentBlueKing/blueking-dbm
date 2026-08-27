# dbm-aidev-init: 基于 bkai-cli，同步 Agent Package（含运行时填充 mcps）
# build context 必须是 backend/dbm_aiagent 目录:
#   cd backend/dbm_aiagent
#   docker build -f bkai-resources/docker/Dockerfile \
#     -t mirrors.tencent.com/build/blueking/dbm-aidev-init:<tag> .

# ---------- extract: 从 config.py 抽出 MCP 绑定（无 Django）----------
FROM python:3.11-slim AS extract
WORKDIR /src
COPY config.py ./
COPY bkai-resources/docker/extract_mcp_bindings.py ./
RUN python extract_mcp_bindings.py ./config.py -o /mcp_bindings.json

# ---------- runtime: bkai-cli + package + render ----------
FROM mirrors.tencent.com/build/blueking/aidev-bkai-cli:latest

WORKDIR /app

# 仅放入 Agent Package 与构建产物，保持镜像精简
COPY bkai-resources/ /app/bkai-resources/
COPY --from=extract /mcp_bindings.json /app/bkai-resources/docker/mcp_bindings.json

RUN pip install --no-cache-dir -r /app/bkai-resources/docker/requirements.txt \
    && chmod +x /app/bkai-resources/docker/entrypoint.sh \
    && chmod +x /app/bkai-resources/docker/extract_mcp_bindings.py \
    && chmod +x /app/bkai-resources/docker/render_agent_configs.py

ENTRYPOINT ["/app/bkai-resources/docker/entrypoint.sh"]
