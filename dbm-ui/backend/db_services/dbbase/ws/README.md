# WebConsole 外部 WebSocket 代理

## 请求链路

```text
浏览器（Cookie + Origin）
  → 外部 dbm-ws /ws/dbbase/webconsole/
  → APIGW（X-Bkapi-Authorization + IS-EXTERNAL: true）
  → 内网 dbm-ws /ws/dbbase/webconsole/
  → 云区域 nginx → DRS
```

外部部署在 `ENABLE_EXTERNAL_PROXY=True` 或 `ENABLE_OPEN_EXTERNAL_PROXY=True`
时自动选择 `ExternalWebConsoleConsumer`。内网部署两个开关均为 False，继续使用
`WebConsoleConsumer`。两端都复用 Channels 登录认证、JWT 验证和 Origin 校验。

外部仅开放固定的 WebConsole 路由和 CONNECT／COMMAND 消息，不接受客户端传入的上游 URL。
外部用户身份取自已登录的 `scope["user"].username`，与 HTTP 代理使用当前登录用户的方式一致；
如果外部与内网用户名不同，需要在现有登录身份体系完成映射，不从消息体接收用户名覆盖。

## 外部配置

```text
ENABLE_EXTERNAL_PROXY=True
EXTERNAL_PROXY_WS_DOMAIN=https://<网关域名>/<网关路径前缀>/<stage>/
```

`EXTERNAL_PROXY_WS_DOMAIN` 默认等于现有 `EXTERNAL_PROXY_DOMAIN`。
实际请求地址是在其后追加 `ws/dbbase/webconsole/`，例如：

```text
https://gateway.example.com/api/bkdbm/prod/
→ wss://gateway.example.com/api/bkdbm/prod/ws/dbbase/webconsole/
```

配置支持 http、https、ws、wss；连接时自动转换为 ws／wss。
公网使用 wss。WSS 校验网关服务端证书，使用运行环境信任的 CA，不携带 DRS 的 mTLS 客户端证书。
内部网关使用私有 CA 时，需要将其安装到外部 dbm-ws 的信任环境。

## 必须配置的 APIGW 路由

本次代码没有修改或发布线上网关资源。部署时必须配置：

1. 网关支持 WebSocket Upgrade 和持续双向通信。
2. GET `/ws/dbbase/webconsole/` 映射到内网 **dbm-ws ASGI 服务**的同一路径，不能指向 WSGI 服务或外部代理自身。
3. 启用应用及用户认证，接受 `X-Bkapi-Authorization`，并向内网注入可验证的 `X-Bkapi-JWT`。
4. 保留服务端设置的 `IS-EXTERNAL: true` 和 `X-DBM-WS-Proxy: 1`。
   后者用于发现错误的回环路由；内网根据已验证 JWT 和前者启用外部脱敏。
5. 网关及 Ingress 的连接、读取和空闲超时需满足长连接和 SQL 执行时间要求。

外部代理不会转发浏览器的 Cookie、Origin、JWT 请求头。
登录 Token 按已有 `WebSocketAPI` 规则放入鉴权 JSON；用户身份及租户信息由服务端组装。

## 业务校验和响应处理

- CONNECT 的集群查询、IAM 校验和选址在内网执行，外部不访问云区域。
- 每条 COMMAND 在内网执行 SQL 校验、Redis 速率／并发限制、DRS 调用、数据脱敏及审计。
- 内网需配置 `BKDATA_SENSI_AGENT_URL` 或 `BKDATA_DATA_TOKEN`，才能进行 SQL 结果脱敏。
- 普通外部代理按 HTTP `after_response` 的规则，将返回 JSON 中的 IPv4 替换为 `*.*.*.*`。
  `ENABLE_OPEN_EXTERNAL_PROXY=True` 时与 HTTP 一致跳过这层 IP 替换。
- 外部代理不处理单据过滤和内部页面跳转，因为该路由只允许 WebConsole 协议。
- 上游响应与关闭帧独立转发，包括 IAM 拒绝时的错误消息和 4403 关闭码。
  异常断开转换为 1011；底层连接异常详情仅记录服务端日志。
- 浏览器断开时关闭上游并取消接收协程；只重试握手建连，不重放 CONNECT 或 COMMAND。

## 联调检查

使用外部地址连接，依次验证：合法用户 CONNECT／COMMAND 成功、无 IAM 权限返回错误后关闭、
SQL 校验及限流生效、敏感数据脱敏和 IP 替换、上游主动关闭及浏览器断开后的资源释放。
检查内网的 `[WEBCONSOLE_COMMAND]` 日志确认记录的是实际用户与集群。
网关不支持 WS 或未配置上述路由时，外部代理只能返回建连失败，不能回退为直接连接云区域。
