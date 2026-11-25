### Description

List platform-wide personal alarm subscription relations. Each record is one account x one cluster, and only clusters that still exist are included. Data is cached for 5 minutes.

The caller must pass `bk_username` in `X-Bkapi-Authorization`, and that user must have the DBM "platform manage" permission.

### Request Parameters

| Field | Type | Required | Description |
| ---- | ---- | ---- | ---- |
| bk_biz_name | string | No | Business name, exact match |
| db_types | string | No | DB types separated by commas, e.g. `mysql,redis` |
| cluster_domain | string | No | Cluster domain, fuzzy match |
| username | string | No | Subscriber account, fuzzy match |
| aggregate | string | No | `cluster`: one row per cluster with `subscribers` and `subscriber_count`; `account`: one row per account with `cluster_count` and `clusters`. Omit to return raw relations |

Empty strings are treated as no filter (an empty `aggregate` means no aggregation). Filters are applied before aggregation.

### Response Example

```json
{
    "result": true,
    "code": 0,
    "message": "",
    "data": [
        {
            "cluster_domain": "cache7.bkaudit2.bk.db",
            "bk_biz_name": "BlueKing Audit",
            "db_type": "redis",
            "username": "januelwang"
        }
    ]
}
```
