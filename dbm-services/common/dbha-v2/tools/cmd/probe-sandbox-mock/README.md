# probe-sandbox-mock

`probe-sandbox-mock`（构建产物为 `dbha-probe-sandbox-mock`）是本地全链路测试工具，模拟：

- gRPC Admin：`GetProbeConfig` / `Heartbeat`
- gRPC Receiver：`PushDataUnary`
- Redis RESP：`PING` / `AUTH` / `INFO`（供 tendiscache 成功采集）

**不随 server 安装，不进入 `make toolkits`。** MySQL 无协议 mock，对应端口走 DetectFailure 上报。

监听地址一律使用环回 `127.0.0.1`。

## 构建

在 `dbha-v2` 根目录：

```bash
make probe-sandbox-mock
# 或
CGO_ENABLED=0 go build -o dbha-probe-sandbox-mock ./tools/cmd/probe-sandbox-mock
```

## 一键全链路

工作目录为 `/tmp/probe-sandbox`（不写入仓库）。`gen-config` 仍会写出 GSE reporter，脚本会调用本工具的 `-patch-yaml` 改成 grpc。

```bash
# 在 dbha-v2 根目录
./scripts/probe-sandbox-full.sh
```

## 手动使用

```bash
./dbha-probe-sandbox-mock \
  --admin-addr 127.0.0.1:19001 \
  --receiver-addr 127.0.0.1:19100 \
  --redis-addr 127.0.0.1:16379 \
  --http-addr 127.0.0.1:18090 \
  --dump /tmp/probe-sandbox/results/receiver.jsonl

dbha-probe gen-config \
  --admin-endpoints 127.0.0.1:19001 \
  --local-ip 127.0.0.1 \
  -o /tmp/probe-sandbox/etc/probe.yaml

./dbha-probe-sandbox-mock \
  -patch-yaml /tmp/probe-sandbox/etc/probe.yaml \
  --receiver-addr 127.0.0.1:19100 \
  --log-path /tmp/probe-sandbox/logs/probe.log
```

HTTP：

- `GET http://127.0.0.1:18090/health`
- `GET http://127.0.0.1:18090/stats`
- `GET http://127.0.0.1:18090/last`
