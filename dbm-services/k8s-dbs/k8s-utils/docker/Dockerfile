# 构建阶段
FROM golang:1.25.11 AS builder

# 部分依赖在 GOPROXY 不可用时可能回源，需要 git；--no-install-recommends 减少镜像层体积
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 构建上下文预期为 dbm-services 目录（同时包含 k8s-dbs 与 common/go-pubpkg）
# direct 作为兜底，避免镜像源缺少模块版本时直接失败
RUN go env -w GOPROXY=https://mirrors.tencent.com/go/,direct

# 先拷贝依赖描述文件，充分利用 Docker layer cache
COPY k8s-dbs/go.mod k8s-dbs/go.sum k8s-dbs/go.work k8s-dbs/go.work.sum ./k8s-dbs/
COPY common/go-pubpkg/go.mod common/go-pubpkg/go.sum ./common/go-pubpkg/

WORKDIR /app/k8s-dbs
RUN GOWORK=/app/k8s-dbs/go.work go mod download

# 再拷贝源码，避免普通代码改动导致依赖下载层失效
COPY k8s-dbs /app/k8s-dbs
COPY common/go-pubpkg /app/common/go-pubpkg

# 使用 k8s-dbs 自带 go.work；不要设置 GOFLAGS=-mod=mod，否则 workspace 模式下会失败
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOWORK=/app/k8s-dbs/go.work \
    go build -trimpath -ldflags="-s -w" -o /app/server ./cmd/ \
    && chmod +x /app/server

# 运行阶段
FROM golang:1.25.11

WORKDIR /app
COPY --from=builder /app/k8s-dbs/k8s-utils ./k8s-utils
COPY --from=builder /app/server ./server

EXPOSE 8000
CMD ["/app/server"]
