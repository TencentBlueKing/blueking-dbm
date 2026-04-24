# Proxy v2

## 包结构

```
pkg/v2/proxy/
├── internal/impl/
│   ├── prepare.go     # 连接建立 + Clean（无 CONNECTION_ID / KILL）
│   ├── is_query.go    # 三分类：query (select/show) / execute (refresh_users) / unsupported
│   ├── do_sql.go      # DoSQL / doQuery / doExecute（带业务 SQL 重试）
│   └── retry.go       # retryAbleErrNum + IsRetryAbleError
└── rpc/
    ├── init.go        # 请求/响应类型定义 + BuildRequestWithDefault
    ├── handler.go     # Handler（单账号，proxy-admin）
    ├── execute.go     # 并发调度 + GlobalSemaphore 限流
    └── oneaddr.go     # 单地址命令执行循环（含 force + 命令白名单校验）
```

## Endpoint

| 方法 | URL | 说明 |
|------|-----|------|
| POST | `/v2/proxy-admin/rpc` | Proxy Admin RPC |

## 核心机制

### 连接

- `prepare.go`：DSN 仅含 `timeout`，不支持 timezone / charset / CONNECTION_ID。使用 `go-sql-driver/mysql` 驱动。
- 连接级重试：`retry-go` 3 次 FixedDelay 2s。
- `Clean`：只做 conn.Close() + db.Close()，不 KILL（proxy 无 CONNECTION_ID 概念）。

### 命令分类（三分类）

`is_query.go` 保持 v1 的三分类策略：

- **query**：`select` / `show` → `QueryxContext`
- **execute**：`refresh_users` → `ExecContext`
- **unsupported**：其他命令 → 拒绝执行，返回 error

与 MySQL 不同，proxy 的命令白名单非常有限，不认识的命令直接拒绝。

### 业务 SQL 重试

`retry.go` + `do_sql.go`：与 MySQL v2 一致，对 1130 / 1045 等瞬时错误最多重试 3 次 FixedDelay 1s。
因为 proxy 底层也是 MySQL 协议，使用相同的 `go-sql-driver/mysql` 错误码。

### Force 模式

`oneaddr.go`：非 force 遇错立即返回，force 时 continue 执行后续命令。
无事务致命错误检测（proxy 场景不涉及事务）。

## 与 MySQL v2 的差异

| 特性 | MySQL v2 | Proxy v2 |
|------|----------|----------|
| 账号 | Admin + WebConsole（2 个 endpoint） | ProxyAdmin（1 个 endpoint） |
| charset / timezone | 支持 | 不支持 |
| CONNECTION_ID + KILL | 支持 | 不需要 |
| 命令分类 | 二分类（query / execute） | 三分类（query / execute / unsupported） |
| 事务致命错误检测 | 支持 | 不适用 |
| complex-rpc | 支持 | 无 |
| WebSocket | 支持 | 无 |

## 待跟进问题

### 1. WebSocket

Proxy v2 目前没有 WebSocket endpoint。v1 也没有。如果将来需要，可参考 MySQL / SQLServer 的 WS 实现。

### 2. 命令白名单扩展

目前 execute 类只有 `refresh_users`。如果 proxy 新增管理命令，需要同步更新 `is_query.go` 的 `executeCmds`。
