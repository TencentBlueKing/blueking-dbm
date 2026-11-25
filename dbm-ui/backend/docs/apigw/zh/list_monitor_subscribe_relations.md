### 功能描述

查询全平台个人告警订阅关系明细，每条记录为「一个账号 × 一个集群」，仅包含当前仍存在的集群。数据缓存 5 分钟。

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username": "admin"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：调用用户名，该用户需具备 DBM「平台管理」权限

### 请求参数

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| bk_biz_name | string | 否 | 业务名称，精确匹配 |
| db_types | string | 否 | DB 类型，多个以逗号分隔，如 `mysql,redis` |
| cluster_domain | string | 否 | 集群域名，模糊匹配 |
| username | string | 否 | 订阅人账号，模糊匹配 |
| aggregate | string | 否 | 聚合方式：`cluster` 按订阅集群聚合，`account` 按订阅账号聚合；不传则返回明细 |

参数为空字符串时视为不过滤（`aggregate` 为空时不聚合）。先过滤，再聚合。

### 返回结果示例

```json
{
    "result": true,
    "code": 0,
    "message": "",
    "data": [
        {
            "cluster_domain": "cache7.bkaudit2.bk.db",
            "bk_biz_name": "蓝鲸审计中心",
            "db_type": "redis",
            "username": "januelwang"
        }
    ]
}
```

### 返回结果参数说明

不聚合时，每条记录为一个账号 × 一个集群：

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| cluster_domain | string | 是 | 集群主访问域名 |
| bk_biz_name | string | 是 | 集群所属业务名称 |
| db_type | string | 是 | 集群所属 DB 类型 |
| username | string | 是 | 订阅人账号 |

`aggregate=cluster` 时，每个集群一条，按订阅人数降序：

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| cluster_domain | string | 是 | 集群主访问域名 |
| bk_biz_name | string | 是 | 集群所属业务名称 |
| db_type | string | 是 | 集群所属 DB 类型 |
| subscribers | string | 是 | 订阅人账号，逗号分隔 |
| subscriber_count | int | 是 | 订阅人数 |

`aggregate=account` 时，每个账号一条，按订阅集群数降序：

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| username | string | 是 | 订阅人账号 |
| cluster_count | int | 是 | 订阅集群数 |
| clusters | string | 是 | 订阅的集群域名，逗号分隔 |
