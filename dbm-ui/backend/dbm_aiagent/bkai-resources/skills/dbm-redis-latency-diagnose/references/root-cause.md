# 根因速查表

## 目录

按集群类型与现象快速定位。文件较大（约 3.7 万字），建议用 `grep -n "根因 N"` 或关键词（如 `XAUTOCLAIM`、`写入洪峰`、`Compaction`）直接跳转到对应小节。

| 根因 | 名称 | 适用类型 |
|---|---|---|
| 1 | RocksDB Range Scan 触发 SST 层级跳跃 | TendisSSD |
| 2 | RocksDB Compaction IO 争抢 | TendisSSD |
| 3 | 单节点 IO 异常（硬件问题） | TendisSSD |
| 4 | 热 key | 通用 |
| 5 | bigkey 阻塞 | 通用 |
| 6A | 单 proxy 阻塞 + 连接分配不均（持续性） | 通用 |
| 6B | 单 proxy 一过性尖刺（自恢复型） | 通用 |
| 7 | TendisSSD HGETALL 全局慢 + 局部 zadd 尖刺 | TendisSSD |
| 8 | TendisPlus 超大 mget 全局慢 | TendisPlus |
| 9 | TendisPlus 超大 Hash HINCRBY+HGETALL 持续高延迟 | TendisPlus |
| 10 | TendisCache HMGET 热点 Hash 持续高延迟 | TendisCache |
| 11 | Proxy→Master 网络链路按机房分区抖动 | 通用 |
| 12 | Twemproxy Pipeline 部分 Key 间歇性失败 | Twemproxy |
| 13 | Proxy QPS 分配严重不均 → 单 proxy 过载 | 通用 |
| 14 | TendisCache HGETALL 短时全局告警 | TendisCache |
| 15 | TendisCache Stream XAUTOCLAIM 消息积压 | TendisCache |
| 16 | 长期高延迟基线 + 瞬时尖刺触发告警 | 通用 |
| 17 | TendisSSD Proxy 层写入洪峰 | TendisSSD |

文件末尾另有「通用区分矩阵」与「决策树」两节，用于多模式交叉比对。

---

## TendisSSD（TwemproxyTendisSSDInstance）

### 根因 1：RocksDB Range Scan 触发大量 SST 层级跳跃

**特征：**
- `zcard`/`zrevrange`/`zrevrangebyscore` 命令延迟异常高（proxy 层 command_latency 数万 ms）
- 其他命令（GET/SET/hGet）延迟相对较低
- 问题集中在数据量大的 shard（通常 `:30011` 端口）
- server log 有大量 `Level subcompaction finished`

**验证指标（当前 MCP 接口不支持，提醒用户手动查）：**
- `internal_key_skipped_count`：range scan 跨 SST 文件的内部 key 跳过次数，高说明数据版本多/delete tombstone 多
- `delete_skipped_count`：range scan 时跳过 delete tombstone 的次数

> 📌 提醒用户：可在 DBM 平台监控页或蓝鲸监控中搜索上述指标名，选对应实例（如 `192.168.2.11:30011`）查看趋势。后续若 MCP 接口支持，可直接通过 metrics 工具拉取。

**建议：**
- 对问题 shard 触发手动 compaction
- 业务侧评估是否可以减少 zrevrange 的扫描范围

---

### 根因 2：RocksDB Compaction IO 争抢

**特征：**
- 所有命令普遍慢（GET/SET/hGet/ZREVRANGE 全部 400~500ms）
- proxy 层全部 IP 延迟均匀偏高（无明显单点）
- server log 全是 `Level subcompaction finished`（compaction 持续进行中）
- 低 QPS 但高延迟（IO 排队，不是流量打满）

**验证指标（当前 MCP 接口不支持，提醒用户手动查）：**
- `user_key_comparison_count`：compaction 过程中 key 比较次数，高说明 compaction 激烈

> 📌 提醒用户：可在 DBM 平台监控页或蓝鲸监控中搜索 `user_key_comparison_count`，选对应实例查看趋势。后续若 MCP 接口支持，可直接通过 metrics 工具拉取。

**建议：**
- Compaction 属于 TendisSSD 正常行为，通常会自行结束
- 如持续不降（超过数小时），考虑对高压节点做整机替换
- 评估是否需要限流降低写入压力

---

### 根因 3：单节点 IO 异常（硬件问题）

**特征：**
- 特定节点延迟显著高于其他（其他 30~60ms，该节点 150ms+）
- 该节点 QPS 低但延迟持续高，从早上开始一直没恢复
- 可能伴随登录失败告警（auth 命令超时触发）
- slave 同步异常告警（主库 IO 忙导致 bgsave/同步跟不上）

**处理：**
- 整机替换工具：`bkdbm-redis-bill.redis_bill_submit_bill_redis_cluster_cutoff`
- 必填：`bk_biz_id`、`cluster_domain`、`cutoff_ips`（字符串数组）
- **⚠️ 高危操作，必须用户二次确认后才能提交**

---

### 根因 7：TendisSSD HGETALL 全局慢 + 局部 zadd 尖刺

**触发场景**：业务频繁对大 Hash Key 执行 `hgetall`，TendisSSD 需要从磁盘读取完整字段列表。后端 Master 层健康（延迟 <10μs），问题在 Proxy→TendisSSD 磁盘读路径。

**识别特征（2026-05-29 ssd002.example.db 实战）**：
- **Proxy 整体延迟**：持续偏高（~0.93ms avg），无明显突增/自恢复，持续数小时
- **命令级延迟（command_latency）**：`hgetall` avg 10~16ms，max 21ms，**全部 proxy 节点同时偏高**（非单点）
- **Master 层**：avg 5~6μs，CPU 1.1%，QPS 均匀分布 ——**后端完全正常**
- **慢日志**：
  - Proxy 节点（`192.168.2.37:50002`）记录 `ZADD recent_game:<userId>` 1410ms（10条），时间精确对应告警时刻
  - Master 节点（`192.168.2.38:30001`）记录 `HGETALL realtime_act_info` 10.44ms（1条，轻度）
- **告警指标**：访问耗时 >1s 的请求数 803/min ≥ 500 阈值（zadd 慢查询贡献了超1秒请求）

**与其他根因的区分**：

| 特征 | 根因7（hgetall全局慢） | 根因2（Compaction IO争抢） | 根因6A（单proxy阻塞） |
|------|----------------------|--------------------------|---------------------|
| 命令分布 | `hgetall` 特别慢，其他命令较轻 | 所有命令普遍慢 | 某proxy上所有命令全慢 |
| Proxy层 | 多节点均匀偏高（avg 0.9~1.5ms）| 多节点均匀高（数十ms）| 单节点极端高，其他正常 |
| Master层 | 完全正常（5~6μs）| 中等偏高 | 完全正常 |
| 持续时长 | 数小时持续（业务访问模式驱动） | 阵发性（compaction周期）| 阵发性（数分钟自恢复）|
| CPU | Master CPU 极低（1~2%）| Master CPU 升高 | 正常 |

**建议处置**：
1. **联系业务方**：排查 `hgetall` 的使用场景——Hash Key 元素数量过多时建议改用 `hget` 按需获取，或 `hscan` 分批读
2. **排查大 sorted set**：`recent_game:<userId>` 格式的 Key 需评估 member 数量，建议定期 `zremrangebyrank` trim
3. **评估数据结构**：若 hgetall 是核心访问路径，可考虑缩减 Hash 字段数或迁移至 TendisPlus（内存型）

---

## TwemproxyRedisInstance / PredixyTendisplusCluster

### 根因 4：热 key

**特征：**
- 单个命令延迟高，集中在少数几个 key
- 慢日志中同一个 key 反复出现
- 某台 master CPU 异常高

**处理：** 业务侧添加本地缓存或对热 key 做拆分

---

### 根因 5：bigkey 阻塞

**特征：**
- HGETALL/SMEMBERS/LRANGE 等全量读命令出现在慢日志
- bigkey 快照中 fields 数量 > 10万

**验证：**
```
bkdbm-redis-query-log.redis_bigkey_log_get_cluster_bigkey_statics
  时间范围覆盖当天早上 07:00~10:00（快照约在 09:45）
```

**处理：** 业务侧拆分大 hash/set，或改用 HSCAN 分批读取

---

### 根因 6A：单 proxy 阻塞 + 客户端连接分配严重不均（持续性）

**变体 6A-2：单 Proxy 连接数骤增（重连风暴/连接泄漏）（2026-07-22 实战归纳）**

**触发场景**：某单一 Proxy 节点在短时间内连接数从正常值骤增至 5x+（如 93→489），导致该 Proxy 延迟飙升至告警值，约 3 分钟后连接数自行回落，延迟恢复。其余 Proxy 和 Master 层全程正常。

**识别特征（2026-07-22 cache149.example.db 实战）**：
- **告警 Proxy**：`192.168.2.39:50149`（上海-临港，**集群内唯一临港 Proxy**，单点）
- 连接数时序：93→92→133→**489（突增）**→99→94→88（3分钟内恢复）
- 延迟：576,886μs（576ms） — 恰好为告警值的 2.25x
- QPS 同步略升（3,039→4,225，+10%），无大幅异常
- 其余 79 个 Proxy：全部正常（420~2,468μs）
- Master 4 台：全部 <1μs
- 命令：incr(avg 1,525μs, max 8,172μs, cv=117.9) + expire(类似)，为典型**反防重放**场景

**与 6A 经典模式的关键区分**：

| 特征 | 根因6A经典（流量持续不均） | 根因6A-2（连接骤增） |
|------|--------------------------|---------------------|
| 连接数分布 | 严重不均（A:B = 28:1，持续） | 骤增后快速恢复（尖刺型） |
| QPS 分布 | 严重不均 | 轻微升高 |
| 持续时间 | 持续不恢复 | **3~5 分钟自恢复** |
| 根因信号 | QPS 路由问题 | 重连风暴/连接池异常 |
| cv 值 | 中等 | **极高（288）**，典型尖刺特征 |
| 单机房唯一性 | 不一定 | 常见（单点 Proxy） |

**排查方向**：
1. 该 Proxy 所在机房客户端在 20:54~20:57 期间是否有重启/重新部署？
2. 客户端连接池配置是否有 max_connections 未限制，导致短时多开连接？
3. 是否有定时任务/批量脚本在该时段打开大量新连接？
4. 该机房 Proxy 是单点，高危——建议扩容冗余

**诊断口诀**：`连接数尖刺型 + QPS 轻微升 + 快速自恢复 = 连接骤增（重连风暴/连接泄漏）`

---

**特征（2026-05-21 cache13.example.db 实测）：**
- **proxy A**：延迟从正常（~1ms）爬升至 239ms → 540ms → **2487ms**，持续 3 分钟后恢复，之后仍有小幅抖动
- **proxy B**：全程 0.1ms，完全不受影响
- proxy A 承接 QPS ~40，proxy B 仅 ~1.5（**比例 28:1**，正常应该接近 1:1）
- master 层：延迟 avg=5μs，CPU=1.1%，QPS=105（完全正常，后端无压力）
- 慢日志：**0 条**（被刷空，不可信）
- proxy A 上所有命令延迟均极高（hget max=5087s，incrby max=8450s，pexpire max=7223s）
- 同一 proxy（`192.168.2.40:50013`）当天上午 09:57~10:07 已有 204 条慢查询（max=10128ms）——**同一 proxy 当天反复发作**

**根因假设：**
- 客户端连接池 DNS / LB 配置未分散，所有流量集中打向同一 proxy 实例
- proxy 进程本身可能存在阻塞（fd 耗尽、单线程队列积压、GC 停顿等）

**排查动作：**
1. 检查 proxy A 上的客户端连接数（`metric_type: connected_clients`）
2. 检查 proxy A 进程状态（fd 数量、CPU 单核使用率）
3. 对比两台 proxy 的 `connected_clients` 和 `qps` 分布是否均衡
4. 联系业务方排查客户端连接分配逻辑（DNS TTL、连接池配置）

**处置：**
- 短期：重启 proxy A 进程（如确认是进程级阻塞）
- 中期：业务侧修复客户端连接分配，确保流量均匀分布至两台 proxy

---

### 根因 6B：单 proxy 一过性尖刺（自恢复型）

**触发场景**：单个 Twemproxy 节点出现短暂延迟尖刺（通常 < 5 分钟），告警由统计窗口内历史尖刺触发，实际已自恢复。常见于 TwemproxyRedisInstance 集群。

**识别特征（2026-06-29 cache026.example.db 实战）**：
- **集群整体延迟**：告警前稳定在 1.5ms，告警时刻突增至 ~20ms，后回落
- **单 proxy 极端异常**：`192.168.2.41` avg=202.62ms，cv=**736.3**，max=12.5s
- **其余 proxy 完全正常**：47 个 proxy avg 全部 1.85~2.37ms
- **latest 已恢复**：异常 proxy `latest=1.34ms` ✅
- **QPS latest 骤降**：avg_qps=247，latest_qps=**3.2**（客户端超时放弃）
- **慢日志关键信号**：最慢查询为 **`type twemproxy_mon`** 106s — 这是 **twemproxy 内部监控探测命令**，非业务命令，说明 proxy 进程自身在那一刻响应极慢
- **command_latency 异常命令**：`expire` avg=32.80ms、`mget` avg=21.73ms、`get` avg=19.61ms（max 极端高：expire 106s、mget 56s），但都是极少数极端慢请求拉高了 avg

**与根因 6A 的关键区分**：

| 特征 | 根因6A（持续阻塞） | 根因6B（一过性尖刺） |
|------|-------------------|---------------------|
| 持续时间 | 持续数分钟~数十分钟 | **< 5 分钟自恢复** |
| QPS 分布 | 严重不均（28:1） | 相对均匀（异常 proxy latest 骤降是超时放弃） |
| latest 延迟 | 仍高位 | **已恢复正常** |
| cv 值 | 中等 | **极高（> 500）** |
| 慢日志特征 | 0 条（被刷空） | 有少量，最慢为 `type twemproxy_mon`（proxy 内部探测） |
| 反复发作 | 是 | 通常单次 |

**诊断口诀**：`cv 极高 + latest 正常 = 尖刺已过，窗口残影`

**建议处置**：
1. 短期：无需操作，已自恢复。观察 QPS latest 是否回升至 avg 水平
2. 如反复发生：排查该 proxy 所在机器网络/磁盘/进程状态；评估摘流或整机替换
3. `type twemproxy_mon` 极慢（>100s）可作为 proxy 进程级卡顿的特征性标志

---

### 根因 8：TendisPlus 超大 mget 全局慢（2026-06-09 实战归纳）

**触发场景**：业务方对 TendisPlus 集群执行超大批量 `mget`（单次 140-260 个 key），触发 RocksDB 大量随机 IO，导致所有 proxy（46个）和所有 master（30个）全部高延迟，触发"访问耗时>1s请求数每分钟≥100"告警。

**识别特征（2026-06-09 tendisplus-3.example.db）**：
- 全部 46 个 proxy 延迟 **835ms-1561ms**，无一正常
- 5 个机房地区（上海-富特/宝信/松江/青浦/花桥）延迟均高（835-1561ms），**排除网络区域因素**
- Master 延迟 **80-142ms**（全部高位，持续稳定，非阵发）
- Master CPU **3-8%**，QPS 正常 —— 排除流量打满
- 慢日志 Top 命令：`mget(subkey len:260)` 405次、`mget(subkey len:158)` 318次、`mget(subkey len:190)` 162次
- 最慢单条：`mget(260 key)` **882ms**，key 前缀 `formal:um:cm:dli`
- `master_series command_latency`：`zremrangebyrank` 296ms、`zadd` 286ms、`zrevrange` 233ms 等 zset 操作全部高延迟

**与其他模式的区分**：

| 特征 | 超大 mget（根因8） | 根因7（hgetall全局慢） | 根因2（Compaction IO） | 写入洪峰 |
|------|-------------------|----------------------|----------------------|---------|
| 慢日志主命令 | `mget(subkey len:N)` | `hgetall` | `zrevrange/zcard` | `hset/hincrby` |
| Master 延迟 | 高（80-142ms，持续） | 正常（5-6μs） | 高（持续） | 正常 |
| Master CPU | 低（3-8%） | 极低（1-2%） | 升高 | 正常-轻微升高 |
| Proxy 地区分布 | 全地区均高 | 全地区均高 | 全地区均高 | 全地区均高 |
| 持续时长 | 持续（业务不改则不恢复） | 持续（数小时） | 分钟~小时级 | 短（<10min 自恢复） |

**建议**：
1. 联系业务方将 mget 批量大小控制在 ≤ 50 个/次
2. 改用分批 pipeline 替代单次大 mget
3. 重点 key 前缀：`formal:um:cm:dli`、`formal:um:cm:li`（UGC 手机端用户数据）

---

### 根因 9：TendisPlus 超大 Hash HINCRBY+HGETALL 持续高延迟（2026-06-18 实战归纳）

**触发场景**：业务方对 TendisPlus 集群高频 `HINCRBY` 写入同一超大 Hash Key，同时并发 `HGETALL` 全量读取，导致 Hash 所在 Master 分片 CPU 飙升（max 36%），P99 持续超 1s，告警持续 33 分钟不自恢复。

**识别特征（2026-06-18 ssd49.example.db）**：
- 告警维度：`cluster_type: PredixyTendisplusCluster`，`instance_role: proxy`，持续 33 分钟
- 全部 8 个 Proxy median 延迟 **23.9~64.5ms**（统计窗口内高位），p95 **68~469ms**，max 最高 1347ms
- Proxy `latest` 延迟 0.9~1.9ms（已有所回落），但 **QPS latest 骤降至均值的 14%**（总 QPS latest 2676 vs avg 18611）
  - **QPS 骤降信号**：业务侧请求已超时放弃重试，集群实际仍处于半瘫状态
- **Master `192.168.2.42` 显著异常**：
  - CPU p95=**35.1%**，max=**36.3%**，远高于其他 Master（<18%）
  - 延迟 avg=0.607ms，p95=0.854ms，max=**4.566ms**
  - 该 Master 两实例（`:30000`、`:30001`）共贡献 **479/2000 条慢日志**（24%）
- 慢日志（16:00~16:40）2000 条（达上限），涉及 9 个实例：
  - `HINCRBY`: 1054 次（**53%**）、`HGETALL`: 530 次（27%）、`GET`: 346 次（17%）
  - 几乎全部 Key 前缀为同一超大 Hash：`1:scores:1:0:1:1000000:900000011:ai_drop:*`
  - 单实例最慢：`ssd49` `192.168.2.43:50049`（告警 Proxy）承接 **998/2000 条（50%）**慢日志
  - Master 最慢：`192.168.2.42:30001` max=**2841ms**，`192.168.2.42:30000` max=**1877ms**

**与根因 8（超大 mget）的关键区分**：

| 特征 | 根因9（HINCRBY+HGETALL 超大Hash） | 根因8（超大 mget） |
|------|----------------------------------|-------------------|
| 慢日志主命令 | `HINCRBY`(53%) + `HGETALL`(27%) | `mget(subkey len:N)` |
| 异常 Master | **单个 Master CPU 极高**（35%+） | 所有 Master 均高（80-142ms） |
| QPS 表现 | **latest 骤降（14% of avg）** | QPS 正常或轻微下降 |
| 延迟表现 | Proxy median 高，latest 有回落 | Proxy 持续高位无回落 |
| Key 特征 | 同一前缀超大 Hash（`uplift:scores:*`）| 批量不同 key mget |
| 持续性 | 持续（业务写入不停则不恢复） | 持续（业务不改则不恢复） |

**判断异常 Master 分片的方法**：
1. `master_stats group_by=[ip]` 按 CPU p95 降序，找 CPU 最高节点
2. 慢日志 `by_instance` 中按 `total_count` 降序，高频实例端口与异常 Master 对应
3. 慢日志中高频 Key 前缀即为打到该 Master 分片的超大 Hash

**QPS 骤降信号解读**：
```
Proxy QPS latest << avg（差距 > 5x）
→ 业务侧客户端连接已大量超时/报错，主动减少请求发送
→ 集群看起来"延迟回落"实际是流量自行减少，不是问题恢复
→ 需检查 Master 层是否仍有告警才能判断是否真正恢复
```

**建议处置**：
1. 🚨 **紧急**：联系 `biz-11/datamining` 业务方
   - 用 `HLEN 1:scores:1:0:ai_drop_01:1:900000011:ai_drop:*` 确认 field 数量
   - **立即停止或限速 `HGETALL`**，改为 `HSCAN` 分批读取
   - 排查 `HINCRBY` 是否有并发批量写入异常
2. 📌 **中期**：拆分超大 Hash（按 ID 分桶，控制单 Key field 数 < 1000）；对 `HGETALL` 加访问频率限制或本地缓存

---

### 根因 13：Proxy QPS 分配严重不均 → 单 proxy 过载 → 全集群延迟偏高（2026-07-17 实战归纳）

**触发场景**：业务客户端连接池/LB 配置未均匀分散，大量请求集中打到某一个 Proxy 实例（QPS 是其他 proxy 的 5~6 倍），导致该 proxy 过载响应变慢，整体 host_latency 停留在 1ms+ 水平，set/type 等命令延迟 1.15~1.29ms。

**识别特征（2026-07-17 tendisplus-2.example.db）**：
- 20 个 proxy 中 **192.168.2.46:50000 avg QPS=4,831**，其余 19 个 proxy avg QPS=660~996（差距 5~6 倍）
- 集群 host_latency avg **1,036μs (1.04ms)**，set avg **1,287μs (1.29ms)**，type avg **1,154μs (1.15ms)** — 对 TendisPlus 偏高（正常应 <500μs）
- Master 层 CPU avg 6%、mem avg 59.1%（接近告警阈值但未触发 latency 告警）
- Proxy 连接数均匀（各 ~1,652），**连接数均匀但 QPS 不均** → 不是连接池空占问题，是**流量集中问题**
- 无活跃 DBM 告警

**与根因 6A 的关键区分**：

| 特征 | 根因13（Proxy QPS分配不均） | 根因6A（单proxy持续阻塞） |
|------|--------------------------|------------------------|
| 异常 proxy QPS | **5~6 倍高于其他 proxy** | 异常 proxy QPS 可能反而低（阻塞积压） |
| 集群整体延迟 | 偏高但未极端（1ms+） | 单 proxy 极端高（2487ms） |
| 连接数分布 | 均匀 | 严重不均 |
| 持续时间 | 持续（业务路由不改则不恢复） | 持续直到重启/摘流 |
| 根因 | **客户端流量集中**（DNS/LB/硬编码 IP） | proxy 进程级阻塞 |

**排查方法**：
1. 拉所有 proxy 的 QPS（`instance_series metric_type=qps`），找 QPS 远超均值（> 3x）的 proxy
2. 拉所有 proxy 的连接数（`instance_series metric_type=connections`），对比是否均匀
3. 拉 `cluster_proxy_stats metric_type=host_latency`，看集群整体延迟是否偏高
4. 拉 `cluster_proxy_stats metric_type=command_latency`，看哪些命令延迟异常
5. 对比连接数 vs QPS：**连接数均匀但 QPS 不均** → 客户端在均匀连接中集中发请求（如同一连接高频调用）

**建议处置**：
1. 🚨 排查业务客户端路由配置：是否有 client 硬编码 proxy IP？连接池是否均衡分配？
2. 📌 将流量分散到其他 proxy（如调整客户端 DNS/LB/连接池配置）
3. ⏳ Master 内存 60% 接近阈值 — 高内存下 RocksDB 写入/读取延迟也会上升，长期需评估扩容

---

### 根因 10：TendisCache HMGET 热点 Hash 持续高延迟（2026-06-30 实战归纳）

**触发场景**：业务对 TendisCache（纯内存 Redis）同一超大 Hash Key 高频 `HMGET`，单次取大量 field，导致全 Proxy 层延迟高企。**Master 层完全正常**（延迟 <0.05ms）。

**识别特征（2026-06-30 cache22.example.db）**：
- **HMGET 单命令主导**：avg 79.5ms，其他命令全部 <10ms，HMGET 占慢日志 95.9%
- **Master 延迟极低**：全部 120 个 Master avg <0.05ms，cv <20
- **Master CPU 正常**：avg 2.7~3.1%，max 5.6%
- **全 Proxy 受影响**：171 个 Proxy 全部延迟偏高（avg 5~52ms，cv >100），非单节点
- **慢日志 Key 高度集中**：同一前缀 `90000000001:1.36.11:wx:1:1:3:1:c:`
- **持续不恢复**：30 分钟后 HMGET avg 仍 84.6ms

**与根因 7（TendisSSD HGETALL）的关键区分**：

| 特征 | 根因10（TendisCache HMGET） | 根因7（TendisSSD HGETALL） |
|------|---------------------------|---------------------------|
| 集群类型 | TendisCache（纯内存） | TendisSSD（磁盘型） |
| 主命令 | HMGET | HGETALL |
| Master 延迟 | <0.05ms | 5~6μs |
| 瓶颈位置 | Proxy→客户端大响应传输 | Proxy→TendisSSD 磁盘读路径 |

**建议处置**：
1. 联系业务方确认热点 Hash Key 的 HMGET 场景
2. 减少 HMGET 单次 field 数量（分批 ≤50 field）
3. 改 HGET 按需取字段，或 Hash 拆分为多个小 Hash
4. 若业务短期无法优化，评估调整告警阈值

> 详见 `references/tendiscache-hmget-hot-hash-2026-06-30.md`

### 根因 14：TendisCache HGETALL 短时全局告警（2026-07-19 实战归纳）

**触发场景**：业务对 TendisCache 大 Hash Key 高频 `hgetall`，全 Proxy 延迟升高触发告警，通常 1~5 分钟自行恢复。与根因10（HMGET）的关键区别：**hgetall 模式短时自恢复，且 Master 层确实完全正常（无需实例级下钻）**。

**识别特征（2026-07-19 cache-3.example.db）**：
- `command_latency`：**`hgetall` avg=6024μs (6ms)，max=65057μs (65ms)**，远超其他命令（get 1.08ms, set 1.06ms）
- 慢日志 `hgetall` 占 84%+（104/123 条），分布在 **124 个 Proxy 实例**（全局性）
- 慢日志 avg 70ms，max 175ms；Key 前缀集中（如 `@prod_999@gamesvr:player:info:<uin>`）
- **Master 延迟 5~11μs，CPU < 20%**——后端完全正常
- 告警短时自恢复（`hgetall` 频率下降后 latest 回落到 ~2ms）
- Proxy host_latency latest 全部正常（1.7~1.9ms）

**与根因10（HMGET 热点 Hash）的区分**：

| 特征 | 根因14（HGETALL 短时） | 根因10（HMGET 持续） |
|------|----------------------|---------------------|
| 主命令 | `hgetall` | `hmget` |
| 持续时间 | **短（1~5min 自恢复）** | 持续不恢复（30min+） |
| Master 实例级 | **确实正常**（无需下钻） | **需下钻**（IP级掩盖热点） |
| 告警后 latest | 已回落 | 仍高 |

**建议处置**：
1. 短期：已恢复无需操作
2. 业务侧将 `hgetall` 改为按需 `hget` 取指定 field
3. 评估 Hash 大小（field 数量 > 100 则 hgetall 开销显著）
4. 如频繁触发告警，需业务配合优化访问模式

> 详见 `references/tendiscache-hgetall-short-burst-2026-07-19.md`

---

### 根因 11：Proxy→Master 网络链路按机房分区间歇性抖动（2026-07-01 实战归纳）

**触发场景**：部分机房的 Proxy 节点到 Master 的网络链路出现间歇性丢包/重传，导致这些 Proxy 出现秒级延迟尖刺，而其他机房 Proxy 完全正常。常见于跨机房部署的 TwemproxyRedisInstance 集群。

**识别特征（2026-07-01 cache0.example.db）**：
- 集群 6 个 Proxy 分布在 3 个机房（深圳-光明2 + 深圳-深宇2 + 深圳-荔景2）
- **光明/深宇 4 个 Proxy**：间歇出现 500ms~1330ms 延迟尖刺，cv=431~759
- **荔景 2 个 Proxy**：全程正常（avg 0.36~0.37ms，max <6ms）
- **Master 层完全正常**：延迟 2~3ms，CPU max 41%（短暂冲高后回落）
- 尖刺**轮流命中**（不同时间打不同 Proxy），间隔不固定
- 慢日志**所有命令均慢**（get/zscore/llen/lrange/lpop），非特定命令
- 连接数正常（30~126），排除连接池问题

**关键区分点 — 为什么不是 Master 问题**：
1. Master 延迟始终 2~3ms（若 Master 阻塞，所有 Proxy 都应受影响）
2. 荔景 Proxy 完全不受影响（若 Master 慢，不应有机房差异）
3. 尖刺不同步（若 Master 卡顿，应所有 Proxy 同时受影响）
4. Master CPU 冲高（11:26~11:30 达 41%）与 Proxy 尖刺时间（11:36~11:40）有 **6~10 分钟时间差**

**与根因6A/6B 的区分**：

| 特征 | 根因11（网络分区抖动） | 根因6A（单proxy阻塞） | 根因6B（一过性尖刺） |
|------|----------------------|---------------------|-------------------|
| 异常 Proxy 数量 | **多个（按机房分组）** | 单个 | 单个 |
| 正常 Proxy | 另一机房全正常 | 其余全正常 | 其余全正常 |
| 尖刺规律 | 轮流命中，间歇性 | 持续高位 | 单次尖刺后恢复 |
| 命令分布 | 所有命令均慢 | 所有命令均慢 | 所有命令均慢 |
| QPS 分配 | 各 Proxy 差异不极端 | 严重不均（28:1） | 相对均匀 |
| latest 状态 | 可能正常也可能仍高 | 仍高位 | 已恢复 |

**建议处置**：
1. 🚨 **紧急**：在异常 Proxy 机器上 `mtr <Master_IP>` 确认丢包率和延迟抖动
2. 📋 确认 Master 所在机房（本例 Master 在同一城市但不同区），排查跨区网络链路
3. 📌 如确认网络问题且短期无法修复：考虑将流量切换到正常机房的 Proxy（荔景），或扩容正常区域 Proxy
4. ⏳ 同时关注是否有大 value Key（如 lrange 2913ms 的列表）加重了网络传输负担

**补充排查 — 大 Value 加重因素**：
- 网络抖动 + 大 value 响应 = 延迟放大效应
- 本例中 `AM:a:b:ALL:d:c:NAMES`（lrange 2913ms）可能是超大列表
- 即使网络恢复，大 value 仍可能在抖动时触发极端延迟
- 建议业务方排查该 Key 长度并优化

---

### 根因 12：Twemproxy Pipeline 部分 Key 间歇性失败（hash-slot 集中 + 后端瞬时阻塞）

**触发场景**：业务一次 pipeline 包含大量命令（如 270 个 hash/set 查询），偶发性出现固定比例的 key（如 87%=236/270）查不到，几秒后恢复正常，交替出现数次。Proxy 和 Redis 日志无明显异常。

**识别特征（2026-07-10 cache.example.db）**：
- **固定 key 受影响**：每次异常都是相同的 236 个 uin 查不到，34 个正常——不是随机丢失
- **间歇性**：异常与正常交替（11:48~11:51 共 5 次爆发，每次持续秒级后自恢复）
- **所有后端在同一台物理机**：12 个 master 实例全部在 192.168.2.47（S5.4XLARGE64）
- **监控层面完全正常**：
  - Proxy host_latency: 530~2100μs（正常范围）
  - Master CPU: avg 6.97%, max 8.40%（极低）
  - Master QPS: 各实例 ~10700~11300（均衡，无热点）
  - 连接数: avg 246, max 268（正常）
  - **99.91% 请求在 4ms 内完成**
  - **该时段无告警触发**
- **架构**：TwemproxyRedisInstance + twemproxy-0.4.1-v36 (12 proxy) + 1 机器 12 实例

**根因分析**：

业务怀疑是 TCP 分包/大包导致超时，但**证据不支持**：
1. 如果是 TCP 分包超时，受影响 key 应该是随机的（取决于 TCP 分段位置），而非固定 236 个
2. 如果是网络层问题，Proxy host_latency 应有明显尖刺，实际没有
3. 延迟分布中 >16ms 区间的请求量极少

**真正根因方向**：Twemproxy 一致性 hash + 后端瞬时阻塞

```
270 个 pipeline 命令 → Twemproxy 按一致性 hash 分发到 12 个分片
  ├─ 236 个 key → hash 到某几个特定分片
  ├─ 34 个 key → hash 到其他分片（正常响应）
  └─ 特定分片出现瞬时阻塞（fork/AOF/内存页面回收/大 key 操作）
      └─ 超过 Twemproxy server_timeout → 该分片所有排队命令返回 error
```

**关键证据链**：
- 固定 key 受影响 → hash 分布集中
- 12 个实例在同一台物理机 → 物理机瞬时 IO 抖动影响特定分片
- 间歇性 + 秒级自恢复 → fork/bgsave/AOF 重写等瞬时事件

**与其他根因的区分**：

| 特征 | 根因12（Pipeline hash-slot 集中） | 根因11（网络分区抖动） | 根因6B（单proxy尖刺） |
|------|----------------------------------|----------------------|---------------------|
| 受影响范围 | 固定 key 子集（按 hash slot） | 按机房分区的 Proxy | 单个 Proxy |
| 监控异常 | **无**（CPU/延迟/QPS 全正常） | Proxy host_latency 有尖刺 | 单 Proxy 延迟极高 |
| 错误表现 | Pipeline 中部分 key 返回 error | 全部请求慢 | 全部请求慢 |
| 恢复模式 | 秒级自恢复，间歇交替 | 分钟级持续 | 分钟级或一过性 |
| 日志异常 | Proxy/Redis 日志无异常 | 可能有网络超时日志 | twemproxy_mon 慢 |

**建议排查**：

| 优先级 | 方向 | 操作 |
|--------|------|------|
| P0 | 查 Twemproxy `server_timeout` 配置 | `cat /data*/twemproxy/*/nutcracker.*.yml` 看 timeout 值 |
| P0 | 查物理机在问题时段是否有 fork/AOF | `redis-cli info persistence` 或查 redis 日志中 bgsave 记录 |
| P1 | 确认 236 个 uin 的 hash 分布 | 用 Twemproxy hash 算法(fnv1a_64)计算 key 落在哪几个分片 |
| P1 | 查 redis slowlog | `redis-cli slowlog get 128` 看该时段有无大 key 操作 |
| P2 | Twemproxy mbuf 配置 | v36 默认 mbuf 16k，270 个 pipeline 的大响应可能触发 mbuf 分配瓶颈 |

**缓解措施（业务暂不能改 pipeline 数量时）**：
1. **增大 Twemproxy `server_timeout`**（如 400ms → 2000ms）——容忍后端偶发慢响应
2. **排除定时持久化**——检查 bgsave/AOF 重写是否恰好在问题时段触发
3. **分散后端部署**——当前 12 个实例全在 1 台物理机，单机 IO 抖动影响所有分片。考虑将实例分散到多台机器
4. **Pipeline 分批**（如果未来可改）——将 270 拆成 3×90，降低单次 pipeline 对单分片的压力

---

### 根因 17：TendisSSD Proxy 层写入洪峰（2026-05-26 实战归纳）

**触发场景**：业务侧（如微信渠道）在短时间内对同一 Key 前缀批量执行 `hset`/`hincrby`，导致多个 Proxy 节点连接队列积压，全集群平均延迟出现尖刺后自行恢复。

**识别特征**：
- 延迟突增集中在 Proxy 层（端口 :50006），Master 层（端口 :30xxx）完全正常（<100μs）
- 多个 Proxy 节点同时受影响（排除单点），呈全局性但持续时间短（3~5 分钟自恢复）
- 慢日志命令：`hset` + `hincrby` 为主，Key 前缀按业务渠道+时间戳分桶（如 `redis_cmd/wx/YYYY.MM.DD/HH:MM`、`ot/wx/lobby/`）
- 监控聚合延迟 (~12 分钟) 导致告警时间比实际写入峰值晚 ~12 分钟

**与其他根因的区分**：

| 特征 | 写入洪峰（本模式） | TendisSSD Compaction（根因2） | 单 Proxy 故障（根因6A） |
|------|-----------------|---------------------|--------------|
| Proxy 延迟 | 多节点同时高 | 多节点同时高 | 单节点极高，其余正常 |
| Master 延迟 | 正常 | 高（IO 争抢） | 正常 |
| 慢日志命令 | hset/hincrby 为主 | zrevrange/zcard 等 range scan | 任意 |
| 持续时长 | 短（<10 分钟，自恢复） | 较长（分钟~小时级） | 持续直到重启/摘流 |
| CPU | 正常或轻微升高 | 明显升高（Compaction 进程） | 单节点高 |

**建议处置**：
1. 联系业务方确认该时段批量写入是否为预期行为（活动峰值 or 异常）
2. 建议写入时间打散（`hincrby` 统计聚合类操作避免按整分钟集中）
3. 如持续发生，评估 Proxy 扩容或限流

---

## 通用区分矩阵

| 模式 | Proxy 延迟 | Master 延迟 | Master CPU | 持续时间 | 命令分布 |
|------|-----------|------------|-----------|---------|---------| 
| Pipeline hash-slot 集中失败（根因12） | **正常**（无异常） | 正常 | 正常（<10%） | 秒级间歇交替 | 固定 key 子集 error |
| Proxy→Master 网络分区抖动（根因11） | **按机房分区**：部分高(秒级)，部分正常 | 正常（2~3ms） | 正常或短暂冲高 | 间歇持续 | 所有命令均慢 |
| Proxy QPS分配不均（根因13） | 全部偏高（1ms+） | 正常（avg 6%） | 正常（<10%） | 持续 | set/type偏高，单proxy QPS 5~6x |
| TendisCache Stream XAUTOCLAIM 积压（根因15） | 全部高（avg 500ms+） | 正常（avg 7%） | 正常 | **持续增长，内存线性上涨** | XAUTOCLAIM(97%+)，同一 Stream key |
| TendisCache HMGET热点Hash（根因10） | 全部高（5~52ms） | **极低**（<0.05ms） | 正常（<3%） | 持续不恢复 | HMGET(95%+) |
| TendisCache HGETALL短时告警（根因14） | 全部偏高（avg 6ms，max 65ms） | **极低**（5~11μs） | 正常（<20%） | 1~5min 自恢复 | hgetall(84%+) |
| TendisPlus 超大mget（根因8） | 全部高（835ms-1561ms） | 高（80-142ms） | 低（3-8%） | 持续 | mget(subkey len:N) |
| TendisPlus 超大Hash HINCRBY+HGETALL（根因9） | median高，latest骤降 | **单节点**极高（CPU 35%+） | **单节点极高** | 持续，QPS自减 | HINCRBY(53%)+HGETALL(27%) |
| TendisSSD HGETALL（根因7） | 全部偏高（~0.93ms） | 正常（5-6μs） | 低（1-2%） | 持续数小时 | 仅 hgetall 高 |
| TendisSSD 写入洪峰 | 多节点同时高 | 正常 | 正常-轻微高 | <10min 自恢复 | hset/hincrby |
| 单 Proxy 故障持续（根因6A） | 单节点极高 | 正常 | 正常 | 持续直到修复 | 任意 |
| 单 Proxy 连接骤增自恢复（根因6A-2） | 单节点极高，cv>200，latest下降 | 正常 | 正常 | **3~5min 自恢复** | incr/expire 为主（连接骤增触发） |
| 单 Proxy 一过性尖刺（根因6B） | 单节点极高，cv>500，latest正常 | 正常 | 正常 | <5min 自恢复 | type twemproxy_mon 极慢 |
| 长期高延迟基线+瞬时尖刺（根因16） | 全部~1s基线 + 单节点极端尖刺 | 正常（45-76ms） | 正常（<18%） | 基线持续+尖刺~15min | 全命令1s+，QPS burst但connections不变 |
| Compaction（根因2） | 高 | 高 | 明显升高 | 分钟~小时级 | range scan 为主 |

## 决策树

```
proxy 全部 IP 均匀高延迟
    └→ 后端 master 整体问题 OR hgetall/hmget 响应大
           ├→ 慢日志: mget(subkey len:N) 为主 → 根因8（超大mget）
           ├→ 慢日志: HINCRBY(50%+)+HGETALL 为主，同一 Key 前缀，单 Master CPU 35%+ → 根因9（超大Hash）
           ├→ 慢日志: XAUTOCLAIM(97%+) 为主，同一 Stream key，avg 500ms+，内存线性增长 → 根因15（TendisCache Stream 消息积压）
           ├→ 慢日志: HMGET(95%+) 为主，Master 延迟极低（<0.05ms） → 根因10（TendisCache HMGET热点Hash）
           ├→ 慢日志: hgetall(84%+) 为主，Master 延迟极低（5~11μs），短时自恢复 → 根因14（TendisCache HGETALL短时告警）
           ├→ command_latency: zcard/zrevrange 极高 → 根因1（range scan）
           ├→ 所有命令均高 + server log compaction → 根因2（IO争抢）
           ├→ hgetall 特别高（10~20ms），其他命令轻度，Master 完全正常 → 根因7（hgetall全局慢）
           └→ 单节点延迟远高于其他 → 根因3（硬件问题）

proxy 部分 IP 高延迟（按机房分组：同一机房多个 proxy 异常，另一机房完全正常）
    └→ 根因11（Proxy→Master 网络分区抖动）
           └→ 验证：异常 proxy 全在同一机房/区域，正常 proxy 在另一机房；Master 延迟正常；mtr 确认丢包

proxy 个别 IP 高延迟（极端：其他 proxy 完全正常，差值 > 100x）
    └→ 单 proxy 自身问题
           ├→ latest 已恢复 + cv 极高（> 500）+ 慢日志有 `type twemproxy_mon` → 根因6B（一过性尖刺，已自恢复）
           ├→ QPS 分配严重不均（某 proxy 承接 > 80% 流量）→ 根因6A（客户端连接不均，持续性）
           ├→ 连接数骤增（3~5x）后自恢复，QPS 轻微升，cv 极高（> 200）→ 根因6A-2（重连风暴/连接泄漏，自恢复型）
           └→ QPS 分配均匀但该 proxy 仍高延迟 → proxy 进程级阻塞（fd 耗尽/内存压力）

proxy 全部 IP 均匀偏高但未极端（1ms+），且某 proxy QPS 远超均值（> 3x），连接数均匀
    └→ 根因13（Proxy QPS分配不均 → 单 proxy 过载）
           └→ 验证：连接数均匀但 QPS 差距大（5~6x）；command_latency set/type 均偏高；Master层正常

proxy 全部 latest ~1s（长期基线），其中单节点 avg/max 极端高（尖刺拉高集群均值触发告警）
    └→ 根因16（长期高延迟基线 + 瞬时尖刺触发告警）
           └→ 验证：① 拉昨天同时段确认 ~1s 是否是长期基线（非今日新增）② 单节点 QPS 暴增（4x+）但 connections 不变 → pipeline/batch 请求洪流 ③ Master 层正常（延迟 <76ms, CPU <18%）④ 问题在 Proxy 层（Proxy vs Master 延迟差距 15-20x）
           └→ 结论必须分两层：告警触发主因（尖刺节点）+ 长期基线问题（架构限制或 SSD IO 特性）

master 某节点 CPU 高 + 高 QPS
    └→ 根因4（热key）或业务流量突增

慢日志 HGETALL/SMEMBERS 高频
    └→ 根因5（bigkey）

⚠️ 告警值 > 500ms 且慢日志为空 → slowlog 被冲刷，以延迟指标为准，忽略慢日志

pipeline 部分 key 间歇性失败（固定 key 子集返回 error，监控无异常）
    └→ 根因12（Twemproxy hash-slot 集中 + 后端瞬时阻塞）
           └→ 验证：失败 key 固定（每次相同）；所有后端在同一物理机；CPU/延迟/QPS 全正常；秒级自恢复
```

## 慢日志的正确理解

TendisSSD slowlog queue 有限（通常 128 条），真正阻塞 1000ms+ 的请求会快速刷掉队列：

- 慢日志记录的是"勉强超阈值"的轻度慢查询（10~20ms），不代表没有更严重的问题
- 慢日志次数多 ≠ 根因；慢日志缺失 ≠ 没有慢查询
- 应以 Step 1~5 的延迟指标为主，慢日志为辅助验证

## 慢日志响应结构（TendisSSD，2026-05-29 实测）

`redis_query_log_query_slowlogs` 对 TendisSSD 集群的返回会同时包含 **proxy 实例**和 **master 实例**的慢日志：

```json
{
  "data": {
    "by_instance": {
      "192.168.2.37:50002": {           // ← Proxy 节点（端口 :50002）
        "duration_stats": { "avg_ms": 1410.09, "max_ms": 1410.11, ... },
        "slowest_query": { "cmd": "ZADD", "key": "recent_game:...", "duration_ms": 1410.11 },
        "top_commands": { "ZADD": 10 },
        "total_count": 10
      },
      "192.168.2.38:30001": {           // ← Master 节点（端口 :30xxx）
        "duration_stats": { "avg_ms": 10.44, "max_ms": 10.44, ... },
        "slowest_query": { "cmd": "HGETALL", "key": "realtime_act_info", "duration_ms": 10.44 },
        "top_commands": { "HGETALL": 1 },
        "total_count": 1
      }
    },
    "summary": { "total_count": 11, "top_commands": { "ZADD": 10, "HGETALL": 1 } }
  }
}
```

**解读要点**：
- proxy 端口 `:50002` 的慢日志反映**客户端→Proxy 路径**的耗时（包含排队等待）
- master 端口 `:30xxx` 的慢日志反映**Proxy→TendisSSD 存储层**的耗时
- 两者都超阈值时，根因在存储层；只有 proxy 超阈而 master 正常时，根因在 proxy 侧（连接积压等）
