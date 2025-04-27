# 构建阶段
FROM golang:1.23 AS builder
# 使用 apt 安装 git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY go.mod go.sum ./
RUN go env -w GOPROXY=https://mirrors.tencent.com/go/
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o main && chmod +x main

# 运行阶段
FROM golang:1.23
WORKDIR /app
COPY --from=builder /app/k8s-utils ./k8s-utils
COPY --from=builder /app/main .
EXPOSE 8080
CMD ["/app/main"]