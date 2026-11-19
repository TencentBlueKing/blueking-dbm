# DNS API 域名检索与操作日志接口文档

## 通用说明

- **基础路径**：`/api/v1/dns/`
- **响应格式**：HTTP 状态码恒为 200，业务结果看 `code`。

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "detail": [],
    "rowsNum": 0
  }
}
```

| 字段 | 说明 |
|---|---|
| `code` | `0` 成功；`10001` 失败（参数错误、数据库错误等，原因见 `message`） |
| `data.detail` | 返回数据 |
| `data.rowsNum` | 查询接口为满足条件的**总条数**（不受分页影响）；写入接口为写入条数 |

- **分页参数**（查询接口通用）：

| 参数 | 默认 | 说明 |
|---|---|---|
| `page` | 1 | 页码，从 1 开始，必须为正整数 |
| `page_size` | 20 | 每页条数，范围 1~1000 |

- **时间格式**：`2006-01-02 15:04:05`，使用服务所在时区。

---

## 1. 域名检索

`GET /api/v1/dns/domain/search`

按域名（模糊）、维护方式、负责人检索域名记录。条件之间是"且"的关系，都不传则返回全部（分页）。

| 参数 | 必填 | 说明 |
|---|---|---|
| `domain_name` | 否 | 域名，模糊匹配（包含即可）；`%`、`_` 按普通字符处理；不会自动补末尾的 `.` |
| `domain_type` | 否 | 维护方式，按值精确匹配：`0` 集群托管，`1` 自主维护。传其他值按该值查询，无数据则返回空结果；不传则不过滤 |
| `manager` | 否 | 负责人，精确匹配 |
| `page`、`page_size` | 否 | 分页，见上 |

**示例**

```bash
curl -G 'http://{host}/api/v1/dns/domain/search' \
  --data-urlencode 'domain_name=mysql' \
  --data-urlencode 'domain_type=0' \
  --data-urlencode 'manager=zhangsan' \
  --data-urlencode 'page=1' \
  --data-urlencode 'page_size=20'
```

**响应**

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "detail": [
      {
        "uid": 1,
        "app": "test",
        "domain_name": "mysql.test.db.",
        "ip": "1.1.1.1",
        "port": 3306,
        "start_time": "2026-11-19T10:00:00+08:00",
        "last_change_time": "2026-11-19T10:00:00+08:00",
        "manager": "zhangsan",
        "remark": "",
        "dns_str": "",
        "status": "1",
        "domain_type": 0,
        "bk_cloud_id": 0
      }
    ],
    "rowsNum": 1
  }
}
```

---

## 2. 写入操作日志

`PUT /api/v1/dns/oplog`

一次可写入多条。**整批校验**：任意一条不合法，则整批都不写入。

**请求体（JSON）**

```json
{
  "logs": [
    {
      "op_time": "2026-11-19 10:30:00",
      "operator": "zhangsan",
      "client_ip": "",
      "op_type": "UPDATE_MANAGER",
      "domain_name": "mysql.test.db.",
      "content": "manager: lisi -> zhangsan"
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `logs` | 是 | 数组，不能为空 |
| `logs[].operator` | 是 | 操作人 |
| `logs[].op_type` | 是 | 操作类型，见下表 |
| `logs[].domain_name` | 是 | 操作域名，需符合域名格式；末尾没有 `.` 会自动补全 |
| `logs[].content` | 否 | 变更内容，文本 |
| `logs[].op_time` | 否 | 操作时间；不传取服务当前时间 |
| `logs[].client_ip` | 否 | 客户端 IP；不传取请求来源 IP |

**操作类型 `op_type`**

| 值 | 含义 |
|---|---|
| `CREATE_DOMAIN` | 创建域名 |
| `UPDATE_MANAGER` | 修改负责人 |
| `UPDATE_REMARK` | 修改备注 |
| `UPDATE_IP` | 修改 IP |
| `DELETE_DOMAIN` | 删除域名 |

**示例**

```bash
curl -X PUT 'http://{host}/api/v1/dns/oplog' \
  -H 'Content-Type: application/json' \
  -d '{"logs":[{"operator":"zhangsan","op_type":"DELETE_DOMAIN","domain_name":"mysql.test.db.","content":"delete all records"}]}'
```

**响应**

```json
{ "code": 0, "message": "OK", "data": { "detail": null, "rowsNum": 1 } }
```

**失败示例**（`message` 会列出每条的问题）

```json
{ "code": 10001, "message": "logs[0]: op_type[XXX] invalid\r\n", "data": { "detail": null, "rowsNum": 0 } }
```

---

## 3. 查询域名级别操作日志

`GET /api/v1/dns/oplog/domain`

| 参数 | 必填 | 说明 |
|---|---|---|
| `domain_name` | 是 | 域名，精确匹配；末尾没有 `.` 会自动补全 |
| `operator` | 否 | 操作人，精确匹配 |
| `op_type` | 否 | 操作类型，传了但不在上表内会报错 |
| `start_time` | 否 | 起始时间（含） |
| `end_time` | 否 | 结束时间（含） |
| `page`、`page_size` | 否 | 分页，见上 |

```bash
curl -G 'http://{host}/api/v1/dns/oplog/domain' \
  --data-urlencode 'domain_name=mysql.test.db.' \
  --data-urlencode 'start_time=2026-11-01 00:00:00' \
  --data-urlencode 'end_time=2026-11-19 23:59:59'
```

---

## 4. 查询全局操作日志

`GET /api/v1/dns/oplog/all`

参数与第 3 个接口相同，区别是**不需要** `domain_name`，查询所有域名的日志。

```bash
curl -G 'http://{host}/api/v1/dns/oplog/all' \
  --data-urlencode 'op_type=DELETE_DOMAIN' \
  --data-urlencode 'page=1' \
  --data-urlencode 'page_size=50'
```

**第 3、4 个接口的响应**（按操作时间倒序）

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "detail": [
      {
        "uid": 12,
        "op_time": "2026-11-19T10:30:00+08:00",
        "operator": "zhangsan",
        "client_ip": "",
        "op_type": "UPDATE_MANAGER",
        "domain_name": "mysql.test.db.",
        "content": "manager: lisi -> zhangsan"
      }
    ],
    "rowsNum": 1
  }
}
```

---