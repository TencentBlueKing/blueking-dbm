# 构建阶段
FROM golang:1.24.2 AS builder
# 使用 apt 安装 git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN go env -w GOPROXY=https://mirrors.tencent.com/go/
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o server ./k8s-dbs/cmd/ && chmod +x server

# 运行阶段
FROM golang:1.24.2
WORKDIR /app
COPY --from=builder /app/k8s-dbs/k8s-utils ./k8s-utils
COPY --from=builder /app/server .
EXPOSE 8080
CMD ["/app/server"]