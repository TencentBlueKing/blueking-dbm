# ha-sandbox-mock

`ha-sandbox-mock`（构建产物为 `dbha-ha-sandbox-mock`）是本地 HA 测试依赖 mock，模拟：

- etcd v3 gRPC：`KV` / `Lease`（含 KeepAlive）/ `Watch` / `Cluster.MemberList` / `Maintenance.Status`
- MySQL 协议：握手、任意账号认证成功、`COM_PING` / `COM_INIT_DB` / `COM_QUIT`；`SELECT VERSION()` 回版本字符串；其它 `SELECT`/`SHOW` 回空结果集；`COM_STMT_PREPARE`/`EXECUTE` 回错误包（避免 GORM 预处理挂死）；其它 `COM_QUERY` 回 OK
- HTTP：`GET /health`
- Admin gRPC 客户端（一次性）：`--admin-grpc-addr 127.0.0.1:15051` 调用 `Heartbeat` 与 `GetProbeConfig` 后退出，用于核对 Admin APM `grpc_*` 指标

**不随 server 安装，不进入 `make toolkits`。** 不启动真实 etcd / mysqld。

监听地址一律使用环回 `127.0.0.1`。

## 构建

在 `dbha-v2` 根目录：

```bash
make ha-sandbox-mock
# 或
CGO_ENABLED=0 go build -o dbha-ha-sandbox-mock ./tools/cmd/ha-sandbox-mock
```

## 一键 Admin reload

工作目录为 `/tmp/ha-sandbox`（不写入仓库）：

```bash
# 在 dbha-v2 根目录
./scripts/ha-sandbox-admin-reload.sh
```

## 手动使用

```bash
./dbha-ha-sandbox-mock \
  --etcd-addr 127.0.0.1:12379 \
  --mysql-addr 127.0.0.1:23306 \
  --http-addr 127.0.0.1:18091

# 对照已启动的 Admin gRPC（环回）
./dbha-ha-sandbox-mock --admin-grpc-addr 127.0.0.1:15051
```
