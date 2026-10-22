---
name: dbm-webconsole-ws
description: >-
  DBM WebConsole WebSocket 前端接入、改造、排障与专项审查。涉及
  /ws/dbbase/webconsole/、CONNECT/COMMAND、集群 tab 会话、USE 数据库切换、
  串行执行、KeepAlive 连接释放、HTTP 降级、408 超时或异常断线时使用。
  不用于 DBA dbconsole 管理控制台、Redis/MongoDB WS 实现或后端部署改造。
---

# DBM WebConsole WebSocket

## 边界与依据

以用户提供的《WebConsole WebSocket 接口文档》为浏览器协议依据；《dbm-ws：独立 WebSocket 服务改造方案》只作架构背景。
将下述接口事实与实施建议区分开；后续文档更新时先核实差异，不用旧示意协议覆盖新接口。
读取 [改造方案](references/implementation-plan.md) 获取代码入口、任务顺序及人工验收矩阵；重新读取当前源码，路径快照不代表代码仍未改造。
遵守项目 AGENTS.md；分析架构先读 dbm-frontend-developer，处理工具箱入口读 dbm-toolbox-developer。
修改 src 前读取编码约定及 known-issues/checks.md；修改 UI 前读取 dbm-designer。
只制定方案时不修改业务代码；执行校验、格式化、构建前征得用户同意。

## 已确认协议

- 同域路径为 /ws/dbbase/webconsole/；HTTPS 页面用 wss，HTTP 页面用 ws。浏览器自动带登录 Cookie，不传 admin 凭据，也不直连 DRS。
- open 后由前端发送 CONNECT；只有收到 error === "" 才视为数据库会话就绪。
- CONNECT 顶层传 request-type、cluster_id；options 仅按文档传 role、charset，body.timeout 为建连超时秒数。
- role 可省略由服务端选择；charset 默认 default；DRS 默认建连超时 2 秒。不要混用 COMMAND 的超时。
- COMMAND 只传 request-type 和 body.command、可选 body.timeout；一条消息一条 SQL，DRS 默认执行超时 600 秒。
- 同一连接串行，响应不回显请求 ID；只保留一个待响应请求，不添加虚构 seq，不做并发队列。
- SELECT 必须带 LIMIT，当前上限 1000；SHOW、DESC、USE、EXPLAIN 按服务端白名单执行。不要自行扩展 SET、写操作或临时表权限。
- 成功回包含 result、rows_affected、error；result 是数据，不是成功标记。业务错误 result 可为 false，code 可选，rows_affected 可缺失。
- 默认限流为每连接 10 条/60 秒、每用户 30 条/60 秒、每用户并行命令 3 条；多个连接共享用户额度，部署配置优先。
- 同一会话持续连接同一实例；换集群或角色关闭重建。断线重连重新 CONNECT，不自动重放 SQL。

```json
{"request-type":"CONNECT","cluster_id":20,"options":{"role":"backend_slave","charset":"utf8mb4"},"body":{"timeout":10}}
```

```json
{"request-type":"COMMAND","body":{"command":"SELECT id FROM business_db.demo_table LIMIT 10;","timeout":30}}
```

## 实施流程

1. 先确认启用范围、role 支持、timezone 和能力开关。MySQL 先灰度；TenDBCluster 的 spider 角色未确认前保留 HTTP，Redis/MongoDB 保持 HTTP。
2. 逐个读取 ConsoleInput 的所有调用方、ClusterTabs、MySQL/TenDBCluster 页面与结果渲染器，不把公共组件等同于 MySQL 专属组件。
3. 保留 queryWebconsole 及 HTTP 默认行为。以可选执行函数接入 ConsoleInput，只给确认支持 WS 的面板注入，不改全局 HTTP 拦截器。
4. 在服务层封装原生 WebSocket、协议解析和单个 pending；在 WebConsole 私有 hook 管理 tab 会话，不创建全局连接池或跨业务框架。
5. 为每个 tab 保存独立 role、charset 和连接状态。后台 tab 保留会话，禁止跟随当前 tab 的全局选项重连。
6. 统一在 tab 确认移除后释放对应会话；清屏只清显示。路由离开、卸载及 pagehide 释放全部会话，释放操作幂等。
7. WS 就绪时允许 USE，HTTP 路径仍保留原有拦截。结果适配显式区分表格、空结果、对象和非查询成功，不把连接信息送进表格渲染器。
8. 验证前征得用户同意；按改造方案中的页面、操作、预期结果交付人工验收。不要为本项目新增测试框架或测试文件。

## 状态与错误守卫

采用 connecting → initializing → ready → executing → ready；断线进入 disconnected，显式释放进入 closed。
区分 WebSocket.OPEN 与数据库 ready。pending 记录 CONNECT 或 COMMAND 类型，不仅靠 connected 布尔值推断消息归属。
从 unknown 校验 JSON 回包；非法 JSON、非法结构或本地等待超时使关联关系失效时，清理 pending 并关闭旧连接，不能放开输入继续复用。
用连接代次标识隔离旧 socket 回调；超时后到达的旧结果不能落入新请求或其他 tab。
执行期间禁用会话参数变更，或明确确认关闭重建；不要静默丢弃在途命令。
关闭和释放必须清理定时器、事件监听，并结算 pending Promise，防止 loading 永久挂起。

| 信号 | 处理 |
| --- | --- |
| 429 / 503 | 展示 error，不自动重试 SQL；连接仍有效时允许后续人工执行 |
| 408 | 结束旧会话，重新建连并 CONNECT；不重放 SQL |
| 消息 4403 / close 4403 | 权限提示去重；不自动重连 |
| close 4401 | 沿用项目登录处理；不自动重连 |
| close 4400 | 检查请求协议，不循环重试 |
| close 1011 / 1006 | 提示异常；有在途命令时说明执行结果未知 |
| close 1000 | 结束会话，不恢复主动关闭的连接 |

握手拒绝可能只出现 error / 1006，不能将 1006 一律判断为登录失效。
第一版建议人工重连；自动重连次数、间隔需另行确认。重连不恢复 USE、变量或其他数据库上下文。
不发送未定义的应用层心跳，不自动执行 SQL 保活；浏览器不能主动发送协议级 Ping。
不在 ws.send 成功后自动降级重发 SQL；HTTP 不是有状态会话的等价替代。

## 完成检查

确认后台 tab 关闭、最后一个 tab 关闭、重新打开同一集群、角色切换、空结果和异常断线都不泄漏连接或错配结果。
确认 Redis/MongoDB 的执行、预检和 success 事件保持兼容；只有明确启用的入口变化。
输出已确认事实、待 PEER 确认项、实际改动范围和真实验证状态；扫描后写 known-issues: 已扫，命中 N 条。
