# v2 — 为什么需要重写

## 背景

v1 的核心执行管线位于 `pkg/rpc_core/`，通过 `RPCEmbedInterface` 接口让 MySQL / Proxy / SQLServer / WebConsole
四个后端共享同一套 `RPCWrapper.Run() → executeOneAddr → queryCmd/executeCmd` 流程。
（Redis / Twemproxy / MongoDB 虽然放在 `rpc_implement/` 目录下，但实际上不走 `rpc_core`，各自独立实现。）

这套设计在早期有效，但随着各后端差异逐渐加大，暴露了以下问题。

## v1 的核心问题

### 1. 并发控制放错位置

v1 的并发控制（`tokenBulkChan`）放在 `RPCWrapper.Run()` 内部（`pkg/rpc_core/run.go:13`），
每次 HTTP 请求各自 `make(chan struct{}, Concurrent)`。这意味着并发上限是 **per-request** 的，
不是 **per-process** 的。当多个请求同时到达，每个请求都可以启动 `Concurrent` 个 goroutine，
进程级实际并发 = 请求数 x Concurrent，完全失控。

v2 改为进程级 `GlobalSemaphore`（`pkg/config/limiter.go`），所有请求共享同一个信号量，
真正做到全局并发上限。

### 2. 共享管线抹平了后端差异

`rpc_core` 强制所有后端走统一的 `MakeConnection → ParseCommand → IsQueryCommand/IsExecuteCommand` 管线。
但各后端差异很大：

- MySQL 需要 charset 探测、timezone、CONNECTION_ID + KILL
- Proxy 不支持 charset/timezone/CONNECTION_ID，命令白名单极窄
- SQLServer 用完全不同的驱动和 DSN，不需要 charset/timezone，角色间命令白名单不同

这些差异被硬塞进同一个 interface 后，出现了：

- `execute_cmds_on_addr.go:72` 用 `db.DriverName() == "mysql"` 判断是否取 CONNECTION_ID，
  SQLServer 直接跳过，导致 connId 永远为 0，超时后 KILL 形同虚设
- SQLServer 通过 Go embedding 嵌入 `SqlserverRPCEmbed` 并覆写方法来缩小只读白名单，
  但 Go embedding 不是继承，覆写从未生效（详见 `pkg/v2/sqlserver/README.md`）

### 3. 重试逻辑冗长且不安全

v1 的 `execute_cmd.go` 手写 for 循环重试 5 次 + sleep 2s，query 和 execute 各写一遍，
逻辑完全重复。且 SQLServer 通过 embedding 也走进了同一套重试，但 `go-mssqldb` 返回的错误类型
不是 `*mysql.MySQLError`，`errors.As` 永远失败，所以 SQLServer 的重试实际上只重试了非 MySQL 错误
（即所有错误都不会命中重试条件，等价于不重试）。

v2 的 MySQL / Proxy 改用 `retry-go` 库，声明式配置重试策略，query/execute 共享同一个 `retryOpts`。
SQLServer v2 显式不做重试（待调研后单独实现）。

### 4. 结果集无保护

v1 的 `queryAtom` 无限 `for rows.Next()` 直到读完，一个 `SELECT * FROM` 大表就能把 DRS 内存撑爆。

v2 加了 `maxQueryRows`（100000 行）和 `maxQueryBytes`（64 MB）双重兜底。

### 5. 日志不一致

v1 日志风格不统一（有 `logger.Info` 有 `slog.Info`，有注释掉的 debug，有冗余的 success/close 日志），
且无法区分来源是 v1 还是 v2。

v2 所有日志统一用 `slog`，带 `v2 {backend}` 前缀，request 入口和出口分别记录完整命令和完整响应。

## v2 的设计原则

1. **每个后端独立一个包**：`pkg/v2/mysql/`、`pkg/v2/proxy/`、`pkg/v2/sqlserver/`，不共享执行管线，
   各自按需实现，不强行抽象
2. **文件名即函数名**：impl 层每个文件只放一个核心函数（`prepare.go` → `Prepare`，`do_sql.go` → `DoSQL`），
   看文件名就能找到函数
3. **进程级并发控制**：`GlobalSemaphore` 保护全局资源，所有后端共用
4. **显式优于隐式**：不依赖 Go embedding 的 promote 行为，用工厂函数 + 显式参数注入账号和命令分类器

## 包结构

```
pkg/v2/
├── README.md            ← 你在这里
├── mysql/               # MySQL + WebConsole（RPC / complex-rpc / WebSocket）
│   ├── README.md
│   ├── internal/impl/   # 连接 / charset探测 / KILL / 重试 / 事务致命错误
│   ├── rpc/
│   └── websocket/
├── proxy/               # Proxy Admin（RPC only）
│   ├── README.md
│   ├── internal/impl/   # 连接 / 三分类命令 / 重试
│   └── rpc/
└── sqlserver/           # SQLServer Admin / DataRead / SySRead（RPC + WebSocket）
    ├── README.md
    ├── internal/impl/   # 连接 / 角色命令白名单
    ├── rpc/
    └── websocket/
```

## 全量 Endpoint

| 方法 | URL | 后端 | 说明 |
|------|-----|------|------|
| POST | `/v2/mysql/rpc` | MySQL | Admin 全权限 RPC |
| POST | `/v2/mysql/complex-rpc` | MySQL | Admin 多 payload 并发 RPC |
| GET  | `/v2/mysql/ws` | MySQL | Admin 全权限 WebSocket |
| POST | `/v2/webconsole/rpc` | MySQL | WebConsole 只读 RPC |
| GET  | `/v2/webconsole/ws` | MySQL | WebConsole 只读 WebSocket |
| POST | `/v2/proxy-admin/rpc` | Proxy | Proxy Admin RPC |
| POST | `/v2/sqlserver/rpc` | SQLServer | Admin 全权限 RPC |
| POST | `/v2/sqlserver/data-read-rpc` | SQLServer | DataRead 业务数据只读 RPC |
| POST | `/v2/sqlserver/sys-read-rpc` | SQLServer | SySRead 系统库只读 RPC |
| GET  | `/v2/sqlserver/ws` | SQLServer | Admin 全权限 WebSocket |
| GET  | `/v2/sqlserver/data-read-ws` | SQLServer | DataRead 业务数据只读 WebSocket |
| GET  | `/v2/sqlserver/sys-read-ws` | SQLServer | SySRead 系统库只读 WebSocket |

## 尚未 v2 化的后端

- Redis / Twemproxy / MongoDB：代码位于 `pkg/rpc_implement/` 目录下，但实际上**不依赖 `rpc_core`**。

  这三个后端的 handler（`RedisRPCEmbed.DoCommand`、`TwemproxyRPCEmbed.DoCommand`、`MongoRPCEmbed.DoCommand`）
  都是直接实现 `gin.HandlerFunc`，没有 import `rpc_core`，不走 `RPCEmbedInterface` / `RPCWrapper` / `generalHandler` 管线。

  - **Redis**：用 `go-redis` 客户端直连，自带命令表白名单 + value size 预检
  - **Twemproxy**：用 `net.Dial` TCP 直连，模拟 netcat 发送原始命令
  - **MongoDB**：通过 `session.Pool` 管理 `mongosh` 子进程，有自己的 session 生命周期管理

  真正依赖 `rpc_core` 管线的只有 MySQL、Proxy、SQLServer、WebConsole，这四个已经全部有 v2 实现。
  因此 `rpc_core` + `generalHandler` 理论上在 v1 全部下线后可以移除。
