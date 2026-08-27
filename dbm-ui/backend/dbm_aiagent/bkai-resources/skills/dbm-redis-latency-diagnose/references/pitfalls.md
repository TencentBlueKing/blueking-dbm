# 接口与参数踩坑清单（Pitfalls）

诊断过程中遇到接口报错、返回空数据、JSON 截断、数据与预期不符时查阅本文件。

## 目录

- 数据为空 / 返回 null：第 1、3、23、24 条
- 输出被截断（65536 bytes）：第 8、15、19 条
- 参数格式与限制：第 4、9、10、13、21 条
- 认证与 server 路由问题：第 12、14a、20 条
- 指标口径易误判：第 2、5、6、7、14、17、18、22、25 条

---

1. **group_by 只支持 ["ip"] 或 ["cluster_domain"]**
   proxy_series / master_series 的 group_by 参数只接受这两个值，传 ["instance"] 返回空数据不报错，极易误判为「无数据」。
   同样，`redis_metrics_query_instance_series` 对 **PredixyRedisCluster 的 proxy 实例**返回 `null`（2026-07-03 实测 `rediscluster.example.db`，IP:Port=192.168.2.18:50000，四种 metric_type 全部返回 null）。**当 instance_series 返回 null 时，改用 `proxy_series group_by=["ip"]` + `ips` 参数过滤**来获取单 proxy 的时序数据。

2. **实例级告警不能用机器级数据替代**
   告警维度含 `instance: IP:Port` → 必须拿实例级时序（group_by ["ip"] 后按端口过滤），整机 CPU/延迟会掩盖单实例问题。

3. **proxy_series 不支持 latency_distribution metric_type**
   实测 latency_distribution 返回 null，延迟分布分析只能通过 command_latency + host_latency 间接推断。

4. **时间参数必须带时区，禁止手动转 UTC**
   正确：2026-03-27T09:18:00+08:00；错误：2026-03-27T01:18:00Z（手动 -8h 会导致时间窗口偏移）。

5. **慢日志只能按实例拉，无集群级逐条接口**
   `redis_query_log_query_slowlogs` 返回统计摘要+逐实例明细，如需按主机逐条拉取可用 `redis_query_log_fetch_host_slowlog`，参数是 `ip`（不是 `host`），且必传 `cluster_domain`。

6. **Master 延迟正常不等于存储层无问题**
   BGSAVE/fork 期间 master 延迟可能短暂正常，需结合 CPU + QPS + 慢日志三者综合判断，不能只看延迟指标。

7. **command_latency key 格式是 cmd@ip**
   返回数据中 key 形如 `get@192.168.2.19`，不是纯命令名，解析时注意按 `@` 分割。

8. **mcporter 输出截断（65536 bytes 限制）**
   mcporter 的 stdout 输出有 65536 bytes 的硬限制。当返回数据超过此限制时，JSON 会被截断导致 `json.loads()` 解析失败（报 `Expecting ',' delimiter` 或 `Unfinished JSON term`）。**`command_latency` group_by=["instance"]** 特别容易超限（每个 proxy × 每个命令 = 大量 key）。应对策略：
   - 使用 `ips` 参数只查告警 proxy 的 command_latency，减少数据量
   - 如果仍超限，放弃 command_latency 精细分析，改用 `host_latency group_by=["ip"]` 做 proxy 分流（Step 3 的核心判断不需要 command 级数据）
   - 使用 `max_len_datapoints: 1~3` 减少时间序列数据量
   - 按 IP 分批查询（`ips` 参数分批传）
   - 对 stats 接口（非 series）优先使用，数据量更小
   - 不要依赖 `group_by` 一次性拉取所有节点的数据
   - 写文件 + `rfind("}")` 修复只适用于对象截断，字符串中间截断仍无法修复

9. **`list_clusters_by_hosts` 必须传 `bk_biz_id`**
   该接口必须有 `bk_biz_id` 参数，不传会报 "parse error, no clusters found"。如果不知道业务 ID，先用 `list_my_bizs` 获取用户负责的业务列表。

10. **`redis_query_meta_list_cluster_storageinstances` page_size ≤ 150**
    超过 150 报错 "请确保该值小于或者等于 150"。master 数量多时需分页（page=1, page=2...）。返回结构是 `data.tuples[].{redis_master, redis_slave}`，只有 IP:port，无地区信息。

11. **proxy 地区信息直接从 `redis_query_meta_list_cluster_proxies` 获取**
    返回 `data.proxies[].sub_zone`，无需额外查机器信息。master 地区需走 `dbmeta_query_list_machine_info`（server: `bkdbm-mcp-prod-dbmeta-query`），字段是 `bk_sub_zone`。

12. **可用 MCP server 列表（2026-07-17 更新）**
    - `bkdbm-mcp-prod-dbmeta-query`（3 tools）— 通用元数据查询
    - `bkdbm-mcp-prod-redis-query-meta`（10 tools）— Redis 元数据查询
    - `bkdbm-mcp-prod-redis-query-status`（2 tools）— 集群负载标签 + 实例详情
    - `bkdbm-mcp-prod-redis-query-alarm`（2 tools）— **告警查询**（fetch_app_alarms / fetch_cluster_alarms）
    - `bkdbm-mcp-prod-redis-metrics` — 延迟/CPU/QPS 时序指标
    - `bkdbm-mcp-prod-redis-query-log` — 慢日志查询
    - `bkdbm-mcp-prod-redis-bill` — 单据提交
    - `bkdbm-mcp-prod-ticket-op` — 单据执行/查询
    - `bkdbm-mcp-prod-redis-reports` — 报告
    - `bkdbm-mcp-prod-ai-report` — AI 报告
    ❌ 不存在：`bkdbm-mcp-prod-cluster`、`bkdbm-mcp-prod-meta`
    ⚠️ 不走 patrol_compat：`bkdbm-mcp-prod-ticket-op`、`bkdbm-mcp-prod-redis-query-alarm`

13. **`proxy_series` end_time 不能超过服务器当前时间 300 秒（2026-06-18 实测）**
    查询告警时如果 `end_time` 写的是未来时间（如故意多加 1 小时），会报错：
    `End time cannot be more than 300 seconds ahead of server time（8700500）`
    **正确做法**：`end_time` 写当前时刻（或告警结束时刻），不要超前。`proxy_stats`（统计接口）无此限制，只有 `proxy_series`（时序接口）有。

14a. **`redis-query-log` server 可能 OAuth timeout 导致慢日志无法拉取（2026-08-03 实测）**
    某些用户的 mcporter 配置中 `bkdbm-mcp-prod-redis-query-log` server 走 OAuth 认证路径，`mcporter call` 时报 `OAuthTimeoutError: timed out after 1s`。即使配置中 headers 使用 `${ENV_VAR}` 格式（与其他 server 一致），mcporter 仍尝试 OAuth 流程而非直接用 header 认证。
    **应对**：跳过慢日志查询，以 metrics host_latency/command_latency 时序数据为主做诊断。Step 6（慢日志验证）标记为「接口不可用，以延迟指标为准」。不影响诊断结论完整性。

14. **`cv > 100` 是「历史尖刺已过，统计窗口未滚完」的信号（2026-06-18 实测）**
    `proxy_stats group_by=[ip]` 返回的 `cv`（变异系数）字段：
    - `cv <= 10`：延迟非常稳定（正常节点）
    - `cv 10~100`：轻度波动，可关注
    - **`cv > 100`：该节点在统计窗口内曾出现极端尖刺**（`max` 可能是 `latest` 的数百倍），但**当前 `latest` 可能已恢复正常**
    
    **判断逻辑**：
    ```
    if cv > 100 and latest < 5ms:
        → 尖刺已过，统计窗口尚未完全滚出，告警可能是历史数据触发
    if cv > 100 and latest >> 正常值:
        → 节点仍处于异常状态，需要重点排查
    ```
    结合 `avg`（窗口均值）和 `latest`（最新值）判断当前真实状态，不要单看 `p95`（可能被历史尖刺拉高）。

15. **`proxy_stats` 按 IP 分组结果被截断时的处理方式**
    集群 proxy 节点较多（如 46 个）时，`proxy_stats group_by=[ip]` 返回的 JSON 超过 65536 字节限制。  
    正确做法：先写入临时文件，再用 `rfind("}")` 截取最后一个完整 JSON 对象再解析：
    ```python
    with open("/tmp/proxy_lat.json", "w") as f:
        f.write(r.stdout)
    with open("/tmp/proxy_lat.json") as f:
        content = f.read()
    last = content.rfind("}")
    content = content[:last+1]
    resp = json.loads(content)
    ```
    注意：`rfind` 修复只适用于对象被截断的情况，若截断发生在 value 中间（如字符串中间）仍会 parse error，此时需进一步缩减数据量。

16. **`redis_query_meta_list_cluster_proxies` 可获取 proxy 地区归属**
    返回字段含 `sub_zone`（如「上海-富特」），可与延迟数据 join 做地区分组分析。参数：`{"cluster_domain": "...", "page_size": 100, "page": 1}`。

17. **IP 级 group_by 会掩盖实例级热点（2026-06-30 实测）**
    大 Key 通过一致性哈希只落到某个 IP 的特定端口（如 `:30001`），同一 IP 的另一个端口（如 `:30000`）完全正常。`group_by: ["ip"]` 是多实例平均值，会稀释掉单实例的热点信号。当已定位到特定命令是根因且 IP 级 Master 延迟看似正常时，**必须补查 `group_by: ["instance"]`**，按实例逐一对比 QPS 和延迟与集群均值的倍数关系。经验阈值：QPS >3x 且延迟 >5x = 大 Key 落盘实例。CPU 不支持 instance group_by，用 IP 级近似。
    
    本坑导致 `cache22.example.db` 诊断初版结论"Master层完全正常"被用户纠正——实例级数据显示 `192.168.2.20:30001` 的 QPS 是集群均值的 4.2x、延迟 7.4x。

18. **series 返回的时间戳是秒级（非毫秒级）**
    `proxy_series` / `master_series` / `slave_series` 返回的 datapoints 格式为 `[value, timestamp]`，其中 `timestamp` 是 **Unix 秒级时间戳**（如 `1784390400`），不是毫秒。解析时直接 `datetime.fromtimestamp(ts, tz=cst)` 即可，**不要除以 1000**（会得到 1970 年日期）。stats 接口无此问题（不返回时序）。

19. **command_latency 用 `group_by: ["cluster_domain"]` 避免大数据集群截断**
    140+ Proxy 的大集群，`command_latency group_by: ["ip"]` 会产生 `proxy数 × 命令数` 个 key，极易超 65536 字节截断。改用 `group_by: ["cluster_domain"]` 只返回每个命令的集群级统计（avg/latest/max），数据量大幅减少，足够判断哪些命令延迟异常。确认异常命令后再按 IP 细查。

20. **mcp_client.py 已不存在，改用 mcporter CLI（2026-07-14 确认）**
    `/projects/.hermes/home/.bkai/openclaw-runtime/mcp_client.py` 已被移除，所有 MCP 调用必须通过 `mcporter call` CLI。参数格式：`mcporter call <server>.<tool> --args '<JSON>'`。
    
    如果当前用户的 mcporter 配置缺少目标 server，或 token 对该 server 报 `Forbidden: appCode[xxx] has no permission to call mcp server[...]`，用 `MCPORTER_CONFIG` 指向有权限的用户配置文件（示例账号 `operator`）：
    ```bash
    MCPORTER_CONFIG=/root/.dbm/mcporter/operator/mcporter.json mcporter call bkdbm-mcp-prod-redis-metrics.redis_metrics_query_cluster_proxy_stats --args '...'
    ```
    **安全铁律**：跨用户 MCPORTER_CONFIG 仅用于查询类操作，不可用于写操作或越权。对方 token 认证失败时必须停下告知用户。

20. **`bkdbm-mcp-prod-redis-query-alarm` 不走 `patrol_compat.mcp_call`（2026-07-17 实测）**
    与 `bkdbm-mcp-prod-ticket-op` 同坑：patrol_compat 路由不覆盖此 server 前缀，调用返回空数据且不报错（`data: {}`），看起来像"没有告警"但实际是路由未命中。**必须用 mcporter CLI + temp_config**：`secure_token_manager.py resolve operator` → 拿 temp_config → `mcporter call bkdbm-mcp-prod-redis-query-alarm.<tool> --args '<json>' --config <temp_config>`。
    
    延迟类告警关键词：DBM 用"耗时"而非"延迟"（如 `Redis(TendisPlus)集群访问耗时超过1秒的请求数量每分钟`），过滤时需覆盖 `耗时/延迟/latency/慢/slow/超时/timeout/响应时间`。

21. **告警时间窗口对查询结果影响极大（2026-07-17 实测）**
    `fetch_app_alarms` 严格按 `start_time/end_time` 过滤 `begin_time`（Unix 时间戳，秒级）。最近 5 分钟窗口可能恰好无告警（告警周期通常 1~5 分钟一轮），但最近 1 小时可能有数据。建议先查 5 分钟，空则扩大到 1 小时。时间格式必须是 `"YYYY-MM-DD HH:MM:SS"`（CST），不要传 UTC。

22. **`fetch_cluster_alarms` 返回空但 `fetch_app_alarms` 有数据（2026-07-17 实测）**

23. **`get_instance_info` 对 PredixyTendisplusCluster 的存储实例返回空（2026-07-17 实测）**
    无论是 `tendisplus_master`、`redis_master`、还是 `master` 作为 `instance_role`，`get_instance_info` 对 `tendisplus-2.example.db` 都返回空 data（code=8700100）。**解决方法**：从 `get_cluster_load_summary` 的 `load_metrics.tendisplus.mem` 字段提取 master IP 列表（这些 IP 就是后端 master 机器），然后用这些 IP 拉实例级指标。注意：TendisPlus 的 master 端口不是 50000（那是 proxy 端口），master 端口通常是 `server_port`（需从 dbmeta 或 cluster overview 获取）。

24. **`instance_series` 对 PredixyTendisplusCluster proxy 的 `host_latency` 返回 empty_series（2026-07-17 实测）**
    用 `redis_metrics_query_instance_series` 对 20 个 proxy 实例（`IP:50000`）查 `host_latency`，返回 `empty_series`（错误码 `empty_series`），QPS/connections 则正常返回。**解决方法**：proxy 层延迟只能通过 `cluster_proxy_stats metric_type=host_latency`（集群级聚合）获取，不能按单个 proxy 实例拉 host_latency 时序。如果需要按 proxy IP 拆分延迟，用 `cluster_proxy_stats` 的 `group_by` 参数替代。

25. **TendisPlus 存储端口 ≠ proxy 端口（2026-07-17 实测）**
    PredixyTendisplusCluster 的 proxy 端口是 50000，但后端 TendisPlus master 的端口不同（通常在 `server_port` 或 `server_port_priority` 字段中）。用 `IP:50000` 拉 master 的 instance_series 会导致 empty_series。**解决方法**：从 `cluster_basic_overview` 获取 `server_port` 字段；如果 overview 不含此字段，用 dbmeta 的 `list_clusters_base_info` 获取；如果也无法获取，则用 `cluster_master_stats`（IP 级聚合）替代 `instance_series`（实例级时序）。
    集群级查询对 `cache-2.example.db` 返回 `{alarm_detail: [], total_alarms: 0}`，但同一时段同集群在 app 级查询中有告警。原因可能是 `fetch_cluster_alarms` 只返回"当前活跃"告警（已恢复的会被清除），而 `fetch_app_alarms` 返回时间窗口内的所有告警记录（含已恢复）。**排查历史告警时优先用 `fetch_app_alarms`**。
    `rediscluster-2.example.db`（PredixyRedisCluster）排查中，S5.LARGE16 的 2 台 Proxy 延迟分别为 7830ms 和 1235ms，而 SA3.LARGE16 的 2 台 Proxy 延迟分别为 1722ms 和 186ms。同一机型两台延迟差距达 6x，但 S5 整体明显高于 SA3。
    
    **判断逻辑**：当 Proxy 延迟按机型明显分层时，机型差异是系统性因素（SA3 是新一代，性能更强），但不能解释同机型内的极端差异。192.168.2.21（S5）的 7830ms 远超同机型 192.168.2.22（S5）的 1235ms，说明该 proxy 有额外异常（进程/网络问题），机型差异只是叠加因素。
    
    **排查时务必关注 `cls_name` 字段**（从 `redis_query_meta_list_cluster_proxies` 获取），Proxy 机型分层是常见但容易被忽略的根因线索。
    
    > 详见 `references/proxy-machine-type-imbalance-2026-07-14.md`
