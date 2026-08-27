# TendisCache HMGET 热点 Hash 模式（2026-06-30 实战归纳）

**集群类型**：TwemproxyRedisInstance（TendisCache / 纯内存 Redis）

**触发场景**：业务对同一超大 Hash Key 高频执行 `HMGET`（一次取大量 field），该 Hash 含大量 field，单次返回数据量大，导致 Proxy 层处理延迟高企。**大 Key 通过一致性哈希落盘到特定 Master 实例，导致这些实例的 QPS、延迟、CPU 均显著高于集群均值。**

## 识别特征（2026-06-30 cache22.example.db 实测）

### 命令级
- `HMGET` avg **79.5ms**，其他命令全部 <10ms — HMGET 是唯一显著异常命令
- `HMGET` max **190.1ms**（跨 171 个 proxy 的聚合值）

### Proxy 层
- 全部 171 个 Proxy 节点延迟均偏高（avg 5~52ms，cv 全部 >100）
- **非单 Proxy 问题**，是全局性
- QPS 分布均匀（100~1600/proxy），排除负载不均

### Master 层（关键判据 — IP 级 vs 实例级）

**IP 级（group_by: ["ip"]）看似正常**：
- 延迟：全部 120 个 Master IP avg <0.05ms，cv <20
- CPU：avg 1.62%，max 3.1%
- QPS：avg 138

**实例级（group_by: ["instance"]）暴露热点**：大 Key 落盘实例的 QPS、延迟、CPU 均显著高于集群均值：

| 实例 | avg QPS | QPS 倍数 | avg 延迟 | 延迟倍数 | CPU(IP级) | CPU 倍数 |
|------|---------|---------|---------|---------|----------|--------|
| **192.168.2.20:30001** | 584 | **4.2x** | 0.065ms | **7.4x** | 1.80% | 1.1x |
| **192.168.2.60:30001** | 491 | **3.6x** | 0.023ms | **2.6x** | 1.24% | 0.8x |
| **192.168.2.61:30000** | 350 | **2.5x** | 0.027ms | **3.1x** | 2.59% | **1.6x** |

**→ 不能说"Master 完全正常"！IP 级平均掩盖了实例级热点。**

**诊断方法论**：当 Step 2/3 已指向特定命令且 IP 级延迟看似正常时，必须补查实例级 `group_by: ["instance"]`，找出 QPS >3x 且延迟 >5x 的实例 = 大 Key 落盘实例。CPU 不支持 instance group_by，用 IP 级近似。

### 慢日志
- 959/1000 条为 HMGET（**95.9%**）
- avg=474.5ms, max=1596.4ms, median=238.5ms
- 涉及 103 个实例（全局性）
- **Key 前缀高度集中**：`9000000000000000001:1.2.11:wx:1:1:3:a:b:`
  - 所有最慢查询的 Key 指向同一 Hash

### 延迟传导链路
业务大 Key HMGET → 落盘实例流量/QPS/延迟飙升 → 所有 Proxy 转发到该实例均变慢 → 集群平均访问耗时超阈值

### 持续性
- 告警首次触发后 30 分钟仍未恢复
- Proxy latest 延迟仍 48.7ms，HMGET avg 仍 84.6ms

## 与其他根因的区分

| 特征 | TendisCache HMGET（本模式） | TendisSSD HGETALL | TendisPlus mget | 写入洪峰 |
|------|---------------------------|--------------------|-----------------|---------|
| 主命令 | HMGET（95%+） | HGETALL | mget(subkey len:N) | hset/hincrby |
| Master IP 级延迟 | 极低（<0.05ms） | 极低（5~6μs） | 高（80-142ms） | 正常 |
| Master 实例级热点 | **有**（QPS 4x, 延迟 7x） | 无 | 全部高 | 无 |
| Master CPU | 正常（<3.1%） | 正常（1.1%） | 低（3-8%） | 正常 |
| Proxy 影响范围 | 全部 | 全部 | 全部 | 多节点 |
| 持续性 | **持续不恢复** | 持续数小时 | 持续 | 短（<10min） |
| 集群类型 | TendisCache | TendisSSD | TendisPlus | 任意 |

**核心区分点**：
1. Master IP 级延迟低 + CPU 正常 → 排除后端全局 IO 争抢
2. **但实例级存在热点**（QPS/延迟远超均值）→ 大 Key 落盘实例是延迟传导源头
3. HMGET 单命令主导 → 不是全局 IO 争抢
4. Key 前缀集中 → 是特定 Hash 的访问模式问题，不是业务流量突增

## 建议处置

1. **联系业务方**：确认热点 Hash Key 的 HMGET 使用场景和频率
2. **减少单次 field 数量**：HMGET 改为分批获取（每批 ≤50 field）
3. **按需取字段**：全量 HMGET 改为 HGET 按需取特定 field
4. **Hash 拆分**：如该 Hash 含大量 field，考虑按业务维度拆分为多个小 Hash
5. **监控**：若业务短期无法优化，评估调整告警阈值或加白
