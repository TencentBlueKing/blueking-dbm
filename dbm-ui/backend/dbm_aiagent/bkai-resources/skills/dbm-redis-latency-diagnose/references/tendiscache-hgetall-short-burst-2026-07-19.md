# TendisCache HGETALL 全局短时告警 — 2026-07-19 实战记录

## 集群信息
- **集群**: `cache-3.example.db`
- **类型**: TwemproxyRedisInstance (TendisCache)
- **区域**: 南京
- **规模**: 30 Master + 140+ Proxy
- **bk_biz_id**: 9000006 (biz-17)

## 告警
- **策略**: Redis(TendisCache)集群平均访问耗时 >= 256.0
- **触发时间**: 2026-07-19 01:23 CST
- **当前值**: 807.63ms
- **持续时间**: ~1分钟，自行恢复

## 诊断数据

### Proxy host_latency (stats, 恢复后)
- 全部 Proxy avg ~1.8~2.0ms，latest ~1.7~1.9ms
- `192.168.2.25` 有历史尖刺 cv=135（max=22.8ms），但 latest=1.9ms

### Master host_latency
- 全部 Master avg 5~11μs，完全正常
- 最高 `192.168.2.26` avg=10.5μs

### Master CPU
- 最高 `192.168.2.27` avg=16.4%，全部 < 20%

### Proxy command_latency (cluster 级)
| 命令 | avg | latest | max |
|------|-----|--------|-----|
| **hgetall** | **6024μs (6ms)** | 2071μs | 65057μs (65ms) |
| zrange | 1893μs | 1178μs | 2703μs |
| zcount | 1330μs | 1305μs | 1567μs |
| get | 1084μs | 1047μs | 1189μs |
| set | 1062μs | 1028μs | 1227μs |

### 慢日志 (00:23~02:23)
- 123 条，分布在 124 个 Proxy 实例
- `hgetall` 104 条 (84.5%)，avg 70.6ms，max 175.3ms
- Key 前缀: `@prod_999@gamesvr:player:info:<uin>`
- 少量 `hmset`(3)、`evalsha`(1)

## 关键技术要点

### 1. series 时间戳是秒级
`proxy_series` / `master_series` 返回 `[value, timestamp]`，timestamp 是 Unix 秒（如 `1784390400`），直接 `datetime.fromtimestamp(ts, tz=cst)` 即可，不要除以 1000。

### 2. command_latency 用 cluster_domain 分组避免截断
140+ Proxy 大集群，`command_latency group_by: ["ip"]` 产生 proxy×命令 个 key，超 65536 字节截断。`group_by: ["cluster_domain"]` 只返回每个命令的集群级统计，数据量可控。

### 3. TendisCache hgetall 与 TendisSSD hgetall 的区别
- **TendisCache**（纯内存）：Master 延迟极低（5~11μs），hgetall 开销在 Proxy 转发大响应体
- **TendisSSD**（磁盘存储）：Master 延迟可能被磁盘 IO 拉高，hgetall 需磁盘读取

## 根因
业务对大 Hash Key `@prod_999@gamesvr:player:info:<uin>` 高频 `hgetall`，Proxy 转发大 Hash 响应体开销大，全部 Proxy 受影响。告警约 1 分钟后自行恢复。

## 建议
- 业务侧将 `hgetall` 改为按需 `hget` 取指定 field
- 评估 Hash 大小（field 数量 > 100 则 hgetall 开销显著）
- 如频繁触发告警，需业务配合优化访问模式
