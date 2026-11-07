# 热点 Key 处置方案

## 方案一：业务侧本地缓存（最快）

在业务服务层（JVM/Go/Python 进程内）增加短 TTL 本地缓存，拦截高频相同 key 的请求。

```python
# Python 示例（cachetools）
from cachetools import TTLCache
_cache = TTLCache(maxsize=1000, ttl=1)  # 1秒 TTL

def get_ranking(key):
    if key in _cache:
        return _cache[key]
    val = redis_client.zrange(key, 0, -1, withscores=True)
    _cache[key] = val
    return val
```

适合：高频读、数据允许1-2秒延迟的场景。

---

## 方案二：Sorted Set 拆分（根本解决）

将 1 个大 sorted set 按 hash 拆分为 N 个子 key，打散到不同 slot。

```python
# 写入时分片
SHARD_NUM = 16
shard_key = f"{base_key}:{hash(member) % SHARD_NUM}"
redis.zadd(shard_key, {member: score})

# 读取时聚合（需业务侧合并）
results = []
for i in range(SHARD_NUM):
    results.extend(redis.zrange(f"{base_key}:{i}", 0, -1, withscores=True))
results.sort(key=lambda x: x[1], reverse=True)
```

注意：Twemproxy 不支持 ZUNIONSTORE 跨 slot，聚合必须在业务侧完成。

---

## 方案三：读写分离（slave 分流）

将 ZRANGE 等只读请求路由到 slave 实例，降低 master 压力。

DBM 操作：在 slave 节点上配置只读入口。

适合：读多写少的 sorted set，且对数据一致性要求不高（允许 replication lag）。

---

## 方案四：限流降级

在 proxy 或业务网关层对该 key 的访问频率限流。

```python
# Redis 令牌桶限流（Lua）
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local current = tonumber(redis.call('get', key) or "0")
if current + 1 > limit then
    return 0
else
    redis.call('incr', key)
    redis.call('expire', key, 1)
    return 1
end
```

---

## 判断选择

| 场景 | 推荐方案 |
|------|---------|
| 读频率 > 1000 QPS，数据变化慢 | 方案一（本地缓存） |
| sorted set > 10万 member | 方案二（拆分） |
| 读多写少，slave 延迟可接受 | 方案三（读写分离） |
| 临时应急 | 方案四（限流） |
