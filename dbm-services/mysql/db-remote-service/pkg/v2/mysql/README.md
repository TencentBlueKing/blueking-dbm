# MySQL v2

## 包结构

```
pkg/v2/mysql/
├── internal/impl/
│   ├── types.go            # SQLResultRow / SQLResultRows 类型定义
│   ├── makeconnection.go   # 连接建立（default charset 探测 + 连接重试）
│   ├── prepare.go          # Prepare：建连 + 取 conn + SELECT CONNECTION_ID()
│   ├── clean.go            # Clean：KILL connId + 关闭 conn/db
│   ├── is_query.go         # IsQueryCommand（含 tdbctl 子命令解析）
│   ├── do_sql.go           # DoSQL / doQuery / doExecute（带业务 SQL 重试）
│   ├── retry.go            # retryAbleErrNum + IsRetryAbleError
│   └── tx_fatal.go         # txFatalErrNum + IsTransactionFatalError
├── rpc/
│   ├── init.go             # 请求/响应类型定义 + BuildRequestWithDefault
│   ├── handler.go          # makeHandler → AdminHandler / WebConsoleHandler
│   ├── complex.go          # ComplexHandler（多 payload 并发）
│   ├── execute.go          # 并发调度 + GlobalSemaphore 限流
│   └── oneaddr.go          # 单地址命令执行循环（含 force + tx_fatal 检测）
└── websocket/
    ├── init.go             # WS 消息类型定义
    ├── command.go          # handleCommand
    └── handler.go          # WS session 管理 + AdminHandler / WebConsoleHandler
```

## Endpoint

| 方法 | URL | 说明 |
|------|-----|------|
| POST | `/v2/mysql/rpc` | Admin 全权限 RPC |
| POST | `/v2/mysql/complex-rpc` | Admin 多 payload 并发 RPC |
| POST | `/v2/webconsole/rpc` | WebConsole 只读 RPC |
| GET  | `/v2/mysql/ws` | Admin 全权限 WebSocket |
| GET  | `/v2/webconsole/ws` | WebConsole 只读 WebSocket |

## 核心机制

### 连接

- `makeconnection.go`：charset 为 `default` 时先建临时连接查 `@@character_set_server`，再用实际 charset 重连。
- `prepare.go`：连接成功后通过 `SELECT CONNECTION_ID()` 获取 server 端 session id。
- `clean.go`：清理时先 `KILL <connId>` 杀后端 session，再关闭 conn / db，防止超时后 SQL 在 server 端继续执行。
- 连接级重试：`retry-go` 3 次 FixedDelay 2s。

### 命令分类

`is_query.go`：query 类命令（use / explain / select / show / desc）走 `QueryxContext`，其余走 `ExecContext`。
特殊处理 tdbctl 子命令：`tdbctl get/show` 是 query，`tdbctl connect ... execute '<sql>'` 按内嵌 SQL 二次判断。

### 业务 SQL 重试

`retry.go` + `do_sql.go`：对 1130 (Host not allowed) / 1045 (Access denied) 等 ACL 锁相关瞬时错误，
最多重试 3 次 FixedDelay 1s。

### Force 模式 + 事务致命错误

`oneaddr.go`：非 force 模式遇错立即返回；force 模式 continue 执行后续命令。
但遇到事务致命错误（`tx_fatal.go`：deadlock 1213 / lock-wait-timeout 1205 / XA-deadlock 1614）时，
即使 force=true 也立即中止 batch，因为 server 已自动回滚事务，继续执行结果不可信。

### WebSocket

- 心跳 30s ping / 60s pong wait
- 空闲超时 10min 自动关闭
- 每条 COMMAND 都经过 GlobalSemaphore 限流（30s acquire timeout）
- CONNECT 不占信号量，仅建连
- 切换地址时自动 KILL 旧 connection

## 与其他 v2 包的对比

MySQL v2 是功能最完整的实现，相比 Proxy / SQLServer 多出以下特性：

| 特性 | MySQL | Proxy | SQLServer |
|------|-------|-------|-----------|
| charset / timezone | 支持 default 自动探测 | 不需要 | 不需要 |
| CONNECTION_ID + KILL | 支持 | 不需要 | 待跟进 |
| 连接重试 | 3 次 | 3 次 | 无 |
| 业务 SQL 重试 | 支持 | 支持 | 待跟进 |
| 事务致命错误检测 | 支持 | 不适用 | 待跟进 |
| complex-rpc | 支持 | 无 | 无 |
| WebSocket | 支持 | 无 | 支持 |
| tdbctl 子命令 | 支持 | 不适用 | 不适用 |
