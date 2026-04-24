# SQLServer v2

## 包结构

```
pkg/v2/sqlserver/
├── internal/impl/
│   ├── prepare.go      # 连接建立 + Clean（无 KILL session）
│   ├── is_query.go     # CommandClassifier 角色命令白名单
│   └── do_sql.go       # DoSQL / doQuery / doExecute
├── rpc/
│   ├── init.go         # 请求/响应类型定义
│   ├── handler.go      # makeHandler → AdminHandler / DataReadHandler / SySReadHandler
│   ├── execute.go      # 并发调度 + GlobalSemaphore 限流
│   └── oneaddr.go      # 单地址命令执行循环
└── websocket/
    ├── init.go          # WS 消息类型定义
    ├── command.go       # handleCommand
    └── handler.go       # WS session 管理 + 3 个 Handler
```

## Endpoint

| 方法 | URL | 说明 |
|------|-----|------|
| POST | `/v2/sqlserver/rpc` | Admin 全权限 RPC |
| POST | `/v2/sqlserver/data-read-rpc` | DataRead 业务数据只读 RPC |
| POST | `/v2/sqlserver/sys-read-rpc` | SySRead 系统库只读 RPC |
| GET  | `/v2/sqlserver/ws` | Admin 全权限 WebSocket |
| GET  | `/v2/sqlserver/data-read-ws` | DataRead 业务数据只读 WebSocket |
| GET  | `/v2/sqlserver/sys-read-ws` | SySRead 系统库只读 WebSocket |

## 与 MySQL v2 的关键差异

| 特性 | MySQL v2 | SQLServer v2 |
|------|----------|--------------|
| charset / timezone | DSN 参数，支持 `default` charset 自动探测 | 不需要，DSN 固定连 `master` 库 |
| 连接重试 | `retry-go` 3 次 FixedDelay | 无重试，直连 |
| CONNECTION_ID / KILL | `SELECT CONNECTION_ID()` + 清理时 `KILL` | 不获取 `@@SPID`，不 KILL |
| 业务 SQL 重试 | 对 1130/1045 等瞬时错误自动重试 | 无重试 |
| 事务致命错误检测 | deadlock/lock-wait-timeout 时即使 force=true 也中止 batch | 无此机制 |
| 命令分类 | `IsQueryCommand` 全局函数 | `CommandClassifier` 实例，按角色区分白名单 |

## v1 bug 修复

`CommandClassifier` 修正了 v1 中 Go struct embedding 导致 DataRead/SySRead 命令白名单失效的问题。

v1 的 `SqlserverDataReadRPCEmbed` / `SqlserverSySReadRPCEmbed` 通过 embedding 嵌入 `SqlserverRPCEmbed`，
并各自覆写了 `InitQueryParseCommands()` / `InitExecuteParseCommands()` 试图缩小白名单。
但 Go 的 embedding 不是继承——被 promote 的 `IsQueryCommand` / `IsExecuteCommand` 调用的始终是
`SqlserverRPCEmbed` 上的方法，覆写从未生效，三个角色实际共用 Admin 级别的完整命令集。

v2 改用 `CommandClassifier` 实例化不同命令集：Admin 用 `AdminCommands`，DataRead/SySRead 用 `ReadOnlyCommands`。

## 待跟进问题

### 1. 业务 SQL 重试

MySQL v2 的 `DoSQL` 使用 `retry-go` 对 `retryAbleErrNum`（1130 Host not allowed / 1045 Access denied）
做最多 3 次 FixedDelay 重试。SQLServer v2 暂未实现类似机制。

需要调研 SQLServer 是否存在等价的瞬时认证/连接错误码，以及 `go-mssqldb` 的错误类型如何匹配。

相关参考：`pkg/v2/mysql/internal/impl/retry.go`

### 2. KILL session

MySQL v2 在 `Prepare` 时通过 `SELECT CONNECTION_ID()` 获取 server 端 session id，
在 `Clean` 时通过 `KILL <connId>` 主动杀掉后端连接，防止超时后 SQL 在 server 端继续执行。

SQLServer 对应的能力是 `SELECT @@SPID` + `KILL <spid>`。
但 v1 从未实现过（`CONNECTION_ID` 逻辑只在 `db.DriverName() == "mysql"` 时执行），
v2 保持与 v1 一致，不做 KILL。

`prepare.go` 和 `do_sql.go` 中已预留了 `@@SPID` / `KILL` 的注释代码，待充分测试后可启用。

### 3. Force 模式下事务致命错误检测

MySQL v2 在 `oneaddr.go` 的命令执行循环中检测 `IsTransactionFatalError`：
遇到 deadlock (1213) / lock-wait-timeout (1205) / XA-deadlock (1614) 时，
即使 `Force=true` 也立即中止 batch，因为 server 端事务已被自动回滚，继续执行结果不可信。

SQLServer v2 的 `oneaddr.go` 在 `Force=true` 时遇到错误会 continue 执行后续命令，
没有类似的事务致命错误拦截。如果 SQLServer 遇到类似死锁场景，force 模式下会继续发送后续 SQL。

需要调研 SQLServer 的等价事务致命错误（如 error 1205 deadlock victim），
以及 `go-mssqldb` 如何暴露这些错误码，然后决定是否补充 `IsTransactionFatalError` 机制。
