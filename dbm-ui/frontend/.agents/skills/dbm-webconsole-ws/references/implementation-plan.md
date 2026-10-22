# WebConsole WebSocket 前端改造方案

状态：待用户确认实施；仅输出方案与技能，不修改业务代码。
依据：用户提供的 WebConsole WebSocket 接口文档、后端独立 dbm-ws 架构讨论稿，以及 2026-10-21 读取的前端源码。接口事实见 SKILL.md；以下是实施建议，不代表后端已实现或联调通过。

## 1. 范围

首批接入 MySQL WebConsole，复用集群 tab、命令历史、清屏、导出及现有暗色布局。TenDBCluster 使用同一方案，但 spider_master/spider_slave 获得后端确认后才启用。
保留 POST /apis/dbbase/webconsole/；Redis、MongoDB 和未启用 WS 的环境维持 HTTP。DBA dbconsole、SQLServer 新入口、后端部署与外部 relay 不在本次前端实施范围。
建议 WS 默认关闭，按环境和支持的集群范围启用；开关字段及来源待 PEER 确认，不臆造后端配置。

## 2. 当前代码与必要改动

源码均位于 src/ 下，实施前重新核对。

| 入口 | 已核实现状 | 必要改动 |
| --- | --- | --- |
| services/source/dbbase.ts | queryWebconsole 返回 error_msg/query | 保留 HTTP 接口，不改返回契约 |
| views/db-manage/common/webconsole/components/console-panel/components/ConsoleInput.vue | MySQL、TenDBCluster、Redis、MongoDB 四个包装组件共用；直接调 HTTP | 增加可选 executeCommand，缺省继续 HTTP；保留历史、导出及 success 行为 |
| views/db-manage/common/webconsole/components/console-panel/mysql/Index.vue | preCheck 拦截 USE | 按实际传输模式放开 USE，HTTP 分支继续拦截 |
| views/db-manage/common/webconsole/components/console-panel/tendbcluster/Index.vue | 同样拦截 USE，共用 MySQL 渲染器 | 确认 spider 角色支持后接入，避免提前启用 |
| views/db-manage/common/webconsole/mysql/Index.vue、tendbcluster/Index.vue | KeepAlive 按集群 ID 缓存；role/charset/timezone 为页面级状态，切 tab 重置 role | WS 模式按 tab 保存参数；避免切 tab 重置或修改后台会话 |
| views/db-manage/common/webconsole/components/ClusterTabs.vue | 最多 8 个 tab；仅关闭当前 tab 发 removeTab，关闭后台 tab 无通知 | 确认移除后对所有 tab 发移除通知；改前逐个读全部调用方 |
| views/db-manage/common/webconsole/components/console-panel/mysql/components/RenderMessage.vue | 只支持字符串行表；空数组可能调用 Object.keys(undefined) | 兼容空结果及实际 WS 数值/null 字段，对象不强转表格 |

## 3. 最小分层

建议仅新增两个实现文件，名称实施时遵循同目录风格：

- services/source/webconsoleWs.ts：专属连接工厂，组装 URL、CONNECT/COMMAND、校验回包、关联单个 pending 和关闭。使用原生 WebSocket，不接入 HTTP 拦截器，不新建通用 WS 框架。
- views/db-manage/common/webconsole/hooks/useWebconsoleSession.ts：页面范围的 tab 会话 Map，提供 ensureSession、execute、closeSession、dispose；管理每个 tab 参数与连接状态，调用服务层。

页面拥有会话 Map，按 cluster ID 寻址，生命周期不依赖 KeepAlive 缓存是否卸载。MySQL/已确认的 TenDBCluster 包装组件向 ConsoleInput 注入执行函数；Redis/MongoDB 不注入。
HTTP 结果维持原状；WS 结果在专属边界适配显示，保留原始 error、code、rows_affected。不要为兼容现有 query 类型把数字、null 或对象盲目转成 string。
只为 WS 增加必要状态和重连入口，不重做控制台 UI；最终提示文案待产品/用户确认并走 t()。

## 4. 会话生命周期

| 事件 | 建议行为 |
| --- | --- |
| 首次打开支持 WS 的 tab | 创建 socket；open 后 CONNECT，成功才开放执行 |
| 切换到另一个 tab | 保留原连接和在途请求，结果写回原 tab；恢复目标 tab 参数 |
| 修改 role/charset | 无在途命令时关闭重建；执行期间禁用修改 |
| 修改 timezone | WS 字段未定义，不静默忽略；默认阻断带时区要求的 WS 启用，或经用户确认在 WS 模式禁用时区控件 |
| 清屏 | 只清显示，不销毁数据库会话；执行中禁止清屏以免迟到结果重新出现 |
| 关闭任意 tab | 通过原关闭确认后，明确释放该 tab；移除事件与清屏分离 |
| 关闭最后一个 tab | 释放会话，清空当前集群，不能留下无效引用 |
| 同一集群重新打开 | 新数据库会话，旧回调不能重新写入历史 |
| 路由离开/组件卸载/pagehide | dispose 全部会话；清理 pending、监听与定时器；pagehide 后页面恢复需重新连接 |
| 异常断线 | 结算 pending；提示结果未知，人工重连，不自动重放 SQL |

不调用 Vue 私有 KeepAlive 缓存 API。第一版保留现有 UI 缓存，连接以显式会话 Map 为准；重新打开 tab 时重新绑定新会话。
每条请求发送前固定 cluster ID、tab 代次及 socket 代次；历史写回不读取可能已变化的当前集群引用。
没有请求 ID：本地等待超时、非法回包后必须关闭旧连接，不能仅清 pending 再执行下一条。浏览器关闭连接不等于 SQL 已取消。

## 5. 灰度、降级及待确认项

HTTP 为环境级/会话开始前的可控备用路径，不做命令发送后的自动重试。USE 成功后更不能静默切 HTTP；用户切换模式时必须提示会话状态丢失。
先提供人工重连，不实现未确认的心跳、8~9 分钟主动关闭、指数退避或自动恢复 USE。

| 待 PEER 确认 | 影响 |
| --- | --- |
| WS 能力开关及实际启用环境、集群类型 | 决定默认路径与灰度范围 |
| backend_master/backend_slave/orphan、spider_master/spider_slave 支持 | 不能直接把 HTTP 枚举视为 WS 保证 |
| timezone 字段及默认语义 | 当前页面有控件，接口未定义，属于启用前兼容阻塞项 |
| 408 总等待时间、是否关闭连接、与 body.timeout 的关系 | 决定本地超时策略；不能照示例把 30 秒作为产品默认 |
| 空闲关闭、心跳和大结果大小 | 决定断线提示和结果处理边界，不自行补协议 |
| USE/空结果/对象结果的真实回包 | 决定渲染和导出行为，未确认类型用 unknown 校验 |
| 登录跳转、权限申请反馈及新增提示文案 | 沿用项目现有行为，不根据 1006 猜测登录失效 |

## 6. 任务顺序与验证

| 阶段 | 任务 | 验证方式 |
| --- | --- | --- |
| P0 协议对齐 | 确认启用范围、角色、timezone、超时与结果样例 | 后端书面确认，并记录待确认项 |
| P1 传输层 | 单 pending、回包校验、错误分流、幂等释放、代次隔离 | 同意校验后 type-check 和改动文件 eslint；浏览器联调 CONNECT/COMMAND |
| P2 页面接入 | 可选执行函数、WS 状态、USE、结果渲染、参数按 tab 保存 | 检查四个包装组件兼容，人工执行查询和 USE |
| P3 生命周期 | 所有 tab 移除通知、关闭会话、页面离开和迟到回包隔离 | 人工关闭当前/后台/最后一个 tab，并重开同一集群 |
| P4 灰度 | 能力开关、HTTP 保留、明确重连反馈 | 切换模式和断线演练，确认无 SQL 重放 |

所有命令在 dbm-ui/frontend 执行。先向用户确认，再按 yarn type-check、改动文件 npx eslint --fix 的顺序执行；修改样式补 stylelint。环境阻塞如实报告，不声称通过。不新建测试文件或引入测试框架。

## 7. 人工验收矩阵

| 页面/操作 | 预期 |
| --- | --- |
| MySQL tab 打开后连续查询 | CONNECT 成功才执行；复用同一 connection_id；同连接不并发 |
| USE 后执行不带库名前缀的查询 | 同一会话中数据库切换有效；重连不自动恢复 |
| 空结果、数值/null 列、非查询成功 | 不报渲染错误，导出保持正确 |
| 查询期间切 tab | 结果只落原 tab，不影响新 tab 的 loading |
| 关闭后台/当前/最后一个 tab，重开同集群 | 会话释放，无旧结果回流，无连接泄漏 |
| 修改角色/字符集，切回其他 tab | 修改只影响对应会话；执行中不能静默切换 |
| 非法 SQL、429/503、4403、握手拒绝 | 错误可读，权限提示去重，不循环重试 |
| 408、断网、非法回包、本地等待超时 | loading 结束，旧连接不复用，SQL 不重放 |
| 清屏、导出、命令历史、离开路由 | 既有功能保留；离开释放全部会话 |
| Redis/MongoDB 与关闭 WS 的 MySQL | 保持现有 HTTP 行为，USE 仍按 HTTP 限制 |

本方案未执行类型校验、格式化或运行时验收；后续实施前需重新扫描 known-issues。
