# dbm-aidev-init: 基于 bkai-init，同步 Agent Package（含运行时填充 mcps）
# build context 必须是 backend/dbm_aiagent：
#   docker build -f bkai-resources/docker/Dockerfile -t dbm-aidev-init:local .

ARG BKAI_INIT_IMAGE=mirrors.tencent.com/build/blueking/bk-aidev-init:0.1.4

# ---------- extract: 从 config.py 抽出 MCP 绑定（无 Django）----------
FROM python:3.11-slim AS extract
WORKDIR /src
COPY config.py ./
COPY bkai-resources/docker/extract_mcp_bindings.py ./
RUN python extract_mcp_bindings.py ./config.py -o /mcp_bindings.json

# ---------- runtime: bkai-init + package + render ----------
FROM ${BKAI_INIT_IMAGE}

WORKDIR /app

# 基础镜像以非 root 运行；安装依赖与赋权需临时切到 root
USER root

COPY bkai-resources/ /app/bkai-resources/
COPY --from=extract /mcp_bindings.json /app/bkai-resources/docker/mcp_bindings.json

RUN pip install --no-cache-dir -r /app/bkai-resources/docker/requirements.txt \
    && chmod +x /app/bkai-resources/docker/entrypoint.sh \
    && chmod +x /app/bkai-resources/docker/extract_mcp_bindings.py \
    && chmod +x /app/bkai-resources/docker/render_agent_configs.py \
    && chown -R 10001:10001 /app/bkai-resources

USER 10001:10001

ENTRYPOINT ["/app/bkai-resources/docker/entrypoint.sh"]
