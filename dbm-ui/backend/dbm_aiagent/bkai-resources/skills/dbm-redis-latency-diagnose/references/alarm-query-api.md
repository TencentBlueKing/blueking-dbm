# DBM Redis Alarm Query API (bkdbm-mcp-prod-redis-query-alarm)

## Server Info

- 2 tools, discovered 2026-07-17
- **Does NOT work via `patrol_compat.mcp_call`** — same routing issue as `bkdbm-mcp-prod-ticket-op`. Returns empty data `{}` without error, looks like "no alarms" but actually routing miss.
- Must use mcporter CLI + temp_config from `secure_token_manager.py resolve`

## Tools

### fetch_app_alarms

Query all alarms for a business within a time range, grouped by alert strategy.

```bash
mcporter call bkdbm-mcp-prod-redis-query-alarm.redis_query_alarm_fetch_app_alarms \
  --args '{"body_param": {"bk_biz_id": 900003, "start_time": "2026-07-17 16:00:00", "end_time": "2026-07-17 17:00:00"}}' \
  --config "$TEMP_CONFIG"
```

### fetch_cluster_alarms

Query alarms for a specific cluster. Returns only currently active alarms (recovered ones are cleared).

```bash
mcporter call bkdbm-mcp-prod-redis-query-alarm.redis_query_alarm_fetch_cluster_alarms \
  --args '{"body_param": {"cluster_domain": "cache-2.example.db", "start_time": "2026-07-17 16:00:00", "end_time": "2026-07-17 17:00:00"}}' \
  --config "$TEMP_CONFIG"
```

⚠️ `fetch_cluster_alarms` may return empty even when `fetch_app_alarms` has data for the same cluster — it only shows currently active alarms.

## Response Structure

```json
{
  "unknown": {
    "<alert_strategy_name>": [
      {
        "alert_name": "DBM#biz-11 Redis(TendisPlus)Proxy主机CPU使用率",
        "begin_time": 1784253720,           // Unix timestamp (seconds)
        "bk_cloud_id": 0,
        "description": "[TendisPlus]Proxy主机CPU使用率 >= 50.0, 当前值50.691866",
        "ip": "192.168.2.7",
        "tags": {
          "app": "biz-11",
          "appid": "900003",
          "cluster_domain": "tendisplus.example.db",
          "cluster_type": "PredixyTendisplusCluster",
          "instance_role": "proxy"
        },
        "target_key": "主机 192.168.2.7"
      }
    ]
  }
}
```

Key points:
- Data nested under `data["unknown"][<strategy_name>]`, not a flat array
- `begin_time` is Unix timestamp (seconds), not a string
- Each strategy name groups alarms of the same type
- `tags.cluster_domain` is the cluster identifier

## Latency Alarm Keywords

DBM uses "耗时" (not "延迟/latency") for latency-type alerts:

| Keyword | Example alert_name |
|---------|-------------------|
| 耗时 | `Redis(TendisPlus)集群访问耗时超过1秒的请求数量每分钟` |
| 延迟 | Less common in DBM alerts |
| 超时 | Timeout-related |
| 慢/slow | Slow query / slow response |

Full filter set: `耗时/延迟/latency/慢/slow/超时/timeout/响应时间/response`

## Time Window Strategy

- Start with 5 minutes (user's request)
- If empty, expand to 1 hour
- `fetch_app_alarms` respects time filtering on `begin_time`
- Alert cycles are typically 1-5 minutes, so a 5-minute window may miss between-cycle gaps

## Batch Query Pattern (all businesses)

1. `list_my_bizs` → get all bk_biz_ids
2. For each biz_id, call `fetch_app_alarms` with mcporter CLI
3. Local filter on `alert_name` / `description` for latency keywords
4. Collect affected `tags.cluster_domain` list → proceed to per-cluster diagnosis
