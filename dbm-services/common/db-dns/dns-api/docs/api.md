# bk-dns-api 接口文档

## 接口总览

基础路径：`/api/v1/dns/`，下表路径均相对于它。`{host}` 为服务监听地址（配置项 `http.listenAddress`）。

| # | 方法 | 路径 | 说明 |
|---|---|---|---|
| 1 | PUT | `/domain` | 添加域名 |
| 2 | DELETE | `/domain` | 删除域名或域名下的实例 |
| 3 | POST | `/domain` | 更新单个实例（修改 IP/端口），可同时改管理人 |
| 4 | POST | `/domain/batch` | 批量更新同一域名下的实例，可同时改管理人 |
| 5 | POST | `/domain/app` | 更新域名所属 app，可同时改管理人 |
| 6 | GET | `/domain` | 按域名/IP 查询域名记录 |
| 7 | GET | `/domain/all` | 查询全部域名记录（ip、域名），供 reload 使用 |
| 8 | GET | `/domain/search` | 域名检索（模糊、分页），返回管理人/更新人/更新时间 |
| 9 | PUT | `/oplog` | 写入操作日志 |
| 10 | GET | `/oplog/domain` | 查询域名级别操作日志 |
| 11 | GET | `/oplog/all` | 查询全局操作日志 |
| 12 | GET | `/config/all` | 查询全部配置 |
| 13 | POST | `/config` | 更新配置项 |

---

## 通用说明

### 响应格式

```json
{
  "code": 0,
  "message": "OK",
  "data": { "detail": [], "rowsNum": 0 }
}
```

| 字段 | 说明 |
|---|---|
| `code` | `0` 成功；`10001` 失败，原因见 `message` |
| `message` | 成功为 `OK`；失败为错误原因，多条校验错误以 `\r\n` 拼接 |
| `data.detail` | 返回数据，写入类接口为 `null` |
| `data.rowsNum` | 查询类：满足条件的记录数（分页接口为不受分页影响的总数）；写入类：影响的行数 |

**HTTP 状态码**：业务错误一律是 `200`，看 `code` 判断。唯一例外是请求体不是合法 JSON（或字段类型不匹配，如给整数字段传了字符串）：这时 HTTP 状态码为 `400`，响应体仍是上面的 JSON 格式、`code` 为 `10001`。该行为依据 gin v1.10.1 源码得出。

**鉴权**：服务代码中没有鉴权逻辑，依赖上游网关或网络隔离。

### 常用格式约定

| 项目 | 规则 |
|---|---|
| 域名 `domain_name` | 3~9 段，段间用 `.` 分隔，每段以字母或数字开头，只含字母、数字、`-`，最长 63 字符。末尾没有 `.` 会自动补全，如 `mysql.test.db` 等价于 `mysql.test.db.` |
| 实例 `ip#port` | IPv4 + `#` + 端口，如 `1.1.1.1#3306`。仅校验形如 `数字.数字.数字.数字`，不校验取值范围 |
| `bk_cloud_id` | 云区域 ID，不传为 `0` |
| 时间格式 | `2006-01-02 15:04:05`，使用服务所在时区；响应中的时间为 RFC3339（如 `2026-11-19T10:00:00+08:00`） |
| 分页 | `page` 从 1 开始，默认 1；`page_size` 范围 1~1000，默认 20。不合法时报错 |
| 多个管理人 | 用英文逗号分隔，如 `zhangsan,lisi`；写入时会去掉空格和重复项 |

### 域名数据模型

`tb_dns_base` 一行代表一个域名下的一个实例（`domain_name + ip + port` 唯一），字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `uid` | int | 主键 |
| `app` | string | 所属业务 |
| `domain_name` | string | 域名，带末尾 `.` |
| `ip` | string | 实例 IP |
| `port` | int | 实例端口，无端口时为 `0` |
| `start_time` | time | 创建时间 |
| `last_change_time` | time | 最近变更时间 |
| `manager` | string | 创建时写入的管理人，之后不再维护，仅在域名还没有 `tb_dns_domain_info` 记录时作为管理人返回 |
| `remark` | string | 备注 |
| `dns_str` | string | 保留字段 |
| `status` | string | 状态，新增时为 `1` |
| `domain_type` | int | 维护方式：`0` 集群托管，`1` 自主维护 |
| `bk_cloud_id` | int | 云区域 ID |

`tb_dns_domain_info` 一行代表一个域名，存域名级公共属性：管理人 `manager`（可多个）、更新人 `updater`、更新时间 `update_time`。联动规则：

| 场景 | 行为 |
|---|---|
| 新建域名（域名在 `tb_dns_base` 中还不存在） | 写入记录，管理人=更新人=请求里的 `manager`；已有同名记录则覆盖 |
| 往已有域名追加实例 | 管理人不变，仅刷新更新人和更新时间 |
| 改实例、改 app、删除 | 刷新更新人和更新时间；传了 `manager` 的更新接口同时覆盖管理人 |
| 记录缺失 | 在该域名第一次被写操作修改时，按 `tb_dns_base` 补全：管理人取该域名下所有记录管理人的并集，更新人先记 `system`，随后被本次操作覆盖 |
| `/domain/search` | 只读，不会补全 |

---

## 1. 添加域名

`PUT /api/v1/dns/domain`

**请求体**

```json
{
  "app": "test",
  "bk_cloud_id": 0,
  "domains": [
    {
      "domain_name": "mysql.test.db.",
      "instances": ["1.1.1.1#3306", "1.1.1.2#3306"],
      "manager": "zhangsan,lisi",
      "remark": "测试集群",
      "domain_type": 0
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `app` | 是 | 业务。服务端未校验，传空会直接写入空值 |
| `bk_cloud_id` | 否 | 默认 `0` |
| `domains[].domain_name` | 是 | 域名，格式见通用说明 |
| `domains[].instances` | 是 | 实例列表，`ip#port`；只传 `ip` 时端口记为 `0` |
| `domains[].manager` | 否 | 管理人，多个用英文逗号分隔；不传默认 `DBAManager` |
| `domains[].remark` | 否 | 备注 |
| `domains[].domain_type` | 否 | 整数，`0` 集群托管，`1` 自主维护；不传为 `0`。传字符串会报 400 |

**行为**

- 整批在一个事务里写入：任意一条校验失败或写库失败，整批都不写入。
- `domain_name + ip + port` 已存在时会触发唯一索引冲突（索引由 `db.auto_migration` 创建），整批失败，`message` 为数据库错误文本。
- 本接口没有 `operator` 参数。新建域名时更新人=管理人；追加实例到已有域名时，更新人记为本次请求的 `manager`。

```bash
curl -X PUT 'http://{host}/api/v1/dns/domain' \
  -H 'Content-Type: application/json' \
  -d '{"app":"test","domains":[{"domain_name":"mysql.test.db.","instances":["1.1.1.1#3306"],"manager":"zhangsan"}]}'
```

**响应**：`rowsNum` 为写入的行数。

```json
{ "code": 0, "message": "OK", "data": { "detail": null, "rowsNum": 1 } }
```

---

## 2. 删除域名

`DELETE /api/v1/dns/domain`（参数在请求体中，`Content-Type: application/json`）

**请求体**

```json
{
  "app": "test",
  "bk_cloud_id": 0,
  "operator": "zhangsan",
  "domains": [
    { "domain_name": "mysql.test.db.", "instances": ["1.1.1.1#3306"] },
    { "domain_name": "redis.test.db.", "instances": [] }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `app` | 是 | 业务，为空报错 |
| `bk_cloud_id` | 否 | 默认 `0` |
| `operator` | 否 | 操作人，记为域名更新人；不传记为 `system` |
| `domains` | 是 | 不能为空数组 |
| `domains[].domain_name` | 二选一 | 域名；`domain_name` 与 `instances` 不能同时为空 |
| `domains[].instances` | 二选一 | 实例列表，`ip#port` 或 `ip` |

**删除范围**（每个 `domains[]` 元素独立处理，且都限定在 `app` + `bk_cloud_id` 内）

| `domain_name` | `instances` | 效果 |
|---|---|---|
| 有 | 空 | 删除该域名下的全部记录 |
| 有 | 非空 | 只删除该域名下匹配的实例 |
| 空 | 非空 | 不限域名，删除匹配的实例 |

实例匹配规则：`ip#port` 精确匹配；只传 `ip`（或 `ip#0`）则匹配该 IP 下所有端口的记录。

**行为**

- 每个域名在一个事务里处理，删除到数据时刷新该域名的更新人和更新时间；域名删光后 `tb_dns_domain_info` 的记录保留。
- 多个 `domains[]` 元素是**逐个**执行的，彼此独立，不在同一个事务里。
- 此接口的错误处理有以下几点需要调用方注意：
  - 参数校验失败（如域名格式错误、实例格式错误、域名与实例同时为空）时，整个请求都不会执行删除。但响应里的 `code` 不稳定：服务端返回的是循环里最后一次域名校验的结果，所以可能是 `code: 10001`（且 `message` 为域名格式错误，仅当最后被校验的域名出错），也可能是 `code: 0`、`rowsNum: 0`。实例格式错误、域名与实例同时为空这两类，通常是 `code: 0`、`rowsNum: 0`，不带原因（只有前面某个域名校验失败且其后没有再校验域名时，才会带出那个域名的错误）。
  - 某个域名删除时的数据库错误会被忽略：该域名的行数记为 `0`，其余域名继续执行，也不会体现在 `code` 里。
  - 所以调用方应以 `rowsNum` 是否符合预期来判断，而不能只看 `code`；发请求前最好自行校验参数。
- 校验失败的详细原因只写在服务日志里，响应不一定返回。

```bash
curl -X DELETE 'http://{host}/api/v1/dns/domain' \
  -H 'Content-Type: application/json' \
  -d '{"app":"test","operator":"zhangsan","domains":[{"domain_name":"mysql.test.db.","instances":[]}]}'
```

**响应**：`rowsNum` 为删除的行数。

---

## 3. 更新单个实例

`POST /api/v1/dns/domain`

把域名下的某个实例替换为新的 `ip#port`。

**请求体**

```json
{
  "app": "test",
  "bk_cloud_id": 0,
  "domain_name": "mysql.test.db.",
  "instance": "1.1.1.1#3306",
  "set": { "instance": "1.1.1.9#3306" },
  "operator": "zhangsan",
  "manager": "zhangsan,lisi"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `app` | 是 | 业务，与 `bk_cloud_id`、域名、旧实例一起定位记录；服务端未校验非空 |
| `bk_cloud_id` | 否 | 默认 `0` |
| `domain_name` | 是 | 域名 |
| `instance` | 是 | 旧实例，必须是 `ip#port`（必须带端口） |
| `set.instance` | 是 | 新实例，必须是 `ip#port` |
| `operator` | 否 | 操作人，记为更新人；不传记为 `system` |
| `manager` | 否 | 域名管理人，整体替换；不传则管理人不变。传了但不含有效管理人（如 `,`）报错 |

**行为**

- 没匹配到记录时不报错，`rowsNum` 为 `0`，此时也不会更新管理人、更新人。
- 匹配到记录时，在同一事务里刷新更新人、更新时间，传了 `manager` 时同时覆盖管理人。

```bash
curl -X POST 'http://{host}/api/v1/dns/domain' \
  -H 'Content-Type: application/json' \
  -d '{"app":"test","domain_name":"mysql.test.db.","instance":"1.1.1.1#3306","set":{"instance":"1.1.1.9#3306"},"operator":"zhangsan"}'
```

**响应**：`rowsNum` 为更新的行数。

---

## 4. 批量更新实例

`POST /api/v1/dns/domain/batch`

对同一个域名批量替换实例。整批在一个事务里，任意一条失败全部回滚。

**请求体**

```json
{
  "app": "test",
  "bk_cloud_id": 0,
  "domain_name": "mysql.test.db.",
  "sets": [
    { "old_instance": "1.1.1.1#3306", "new_instance": "1.1.1.9#3306" },
    { "old_instance": "1.1.1.2#3306", "new_instance": "1.1.1.10#3306" }
  ],
  "operator": "zhangsan",
  "manager": "zhangsan,lisi"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `app`、`bk_cloud_id`、`domain_name` | 同接口 3 | |
| `sets[].old_instance` | 是 | 旧实例，`ip#port` |
| `sets[].new_instance` | 是 | 新实例，`ip#port` |
| `operator`、`manager` | 否 | 同接口 3 |

`rowsNum` 为所有 `sets` 更新行数之和；`sets` 为空数组时不做任何修改，返回 `code: 0`、`rowsNum: 0`。

---

## 5. 更新域名 app

`POST /api/v1/dns/domain/app`

**请求体**

```json
{
  "bk_cloud_id": 0,
  "domain_name": "mysql.test.db.",
  "app": "old_app",
  "new_app": "new_app",
  "operator": "zhangsan",
  "manager": "zhangsan,lisi"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `domain_name` | 是 | 域名，末尾自动补 `.`，不做格式校验 |
| `app` | 是 | 当前 app，仅用于“记录是否存在”的预检查 |
| `new_app` | 是 | 新 app |
| `bk_cloud_id` | 否 | 默认 `0` |
| `operator` | 否 | 操作人，记为更新人；不传记为 `system` |
| `manager` | 否 | 域名管理人，整体替换；不传则不变 |

**行为**

- 预检查：按 `domain_name` + `app` 查询不到记录时报错 `query domain record is 0. please check params`。
- 更新范围是该 `domain_name` + `bk_cloud_id` 下的**所有**记录，不是只更新 `app` 匹配的记录。
- 传了 `manager` 时，即使 `app` 没有变化（影响行数为 `0`）也会更新管理人、更新人、更新时间。

---

## 6. 按域名/IP 查询域名记录

`GET /api/v1/dns/domain`

| 参数 | 必填 | 说明 |
|---|---|---|
| `domain_name` | 与 `ip` 至少一个 | 域名，可重复传多个；末尾自动补 `.`，不做格式校验 |
| `ip` | 与 `domain_name` 至少一个 | `ip` 或 `ip#port`，可重复传多个；格式不对报错。只传 `ip` 匹配该 IP 的所有端口 |
| `app` | 否 | 业务，可重复传多个 |
| `bk_cloud_id` | 否 | 默认 `0` |
| `columns` | 否 | 只返回指定字段，可重复传，取值为 `tb_dns_base` 的字段名；不传返回全部字段。写错的字段名会被忽略 |

多个条件之间是 AND；同一个参数传多个值是 OR（`IN`）。该接口不分页，不带 `page`、`page_size`。

```bash
curl -G 'http://{host}/api/v1/dns/domain' \
  --data-urlencode 'domain_name=mysql.test.db' \
  --data-urlencode 'ip=1.1.1.1' \
  --data-urlencode 'columns=domain_name' \
  --data-urlencode 'columns=ip' \
  --data-urlencode 'columns=port'
```

**响应**：`detail` 为对象数组，对象只含请求的字段。

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "detail": [ { "domain_name": "mysql.test.db.", "ip": "1.1.1.1", "port": 3306 } ],
    "rowsNum": 1
  }
}
```

**注意**：本接口的 `manager` 是 `tb_dns_base.manager`，且没有 `updater`、`update_time`，可能与 `/domain/search` 返回的管理人不一致。需要域名级管理人时请用接口 8。

---

## 7. 查询全部域名记录

`GET /api/v1/dns/domain/all`

供 reload 程序使用，返回指定云区域下所有记录的 `ip` 和 `domain_name`，不分页。

| 参数 | 必填 | 说明 |
|---|---|---|
| `bk_cloud_id` | 否 | 默认 `0` |

```bash
curl -G 'http://{host}/api/v1/dns/domain/all' --data-urlencode 'bk_cloud_id=0'
```

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "detail": [ { "ip": "1.1.1.1", "domain_name": "mysql.test.db." } ],
    "rowsNum": 1
  }
}
```

---

## 8. 域名检索

`GET /api/v1/dns/domain/search`

按域名（模糊）、维护方式、管理人检索域名记录，分页，按 `uid` 升序。条件之间是“且”的关系，都不传返回全部。

| 参数 | 必填 | 说明 |
|---|---|---|
| `domain_name` | 否 | 域名，模糊匹配（包含即可）；`%`、`_` 按普通字符处理；不会自动补末尾的 `.` |
| `domain_type` | 否 | 维护方式，整数，精确匹配：`0` 集群托管，`1` 自主维护。其他整数按该值查询，无数据返回空结果；不是整数也返回空结果；不传则不过滤 |
| `manager` | 否 | 管理人。域名有多个管理人（逗号分隔）时，命中任意一个即可 |
| `page`、`page_size` | 否 | 分页，见通用说明 |

**返回字段**：`tb_dns_base` 的全部字段，加上：

| 字段 | 说明 |
|---|---|
| `manager` | 域名管理人。有 `tb_dns_domain_info` 记录时取自该表（覆盖 `tb_dns_base.manager`，可能有多个，逗号分隔）；没有记录时取 `tb_dns_base.manager` |
| `updater` | 域名最近一次变更（新增/修改/删除）的操作人；没有记录时为空串 |
| `update_time` | 域名最近一次变更时间；没有记录时取该行的 `last_change_time` |

检索是只读的：不会补全 `tb_dns_domain_info`，所以一直没被改过的老域名会返回 `tb_dns_base` 的管理人。`manager` 过滤同理，作用于上述生效的管理人。

```bash
curl -G 'http://{host}/api/v1/dns/domain/search' \
  --data-urlencode 'domain_name=mysql' \
  --data-urlencode 'domain_type=0' \
  --data-urlencode 'manager=zhangsan' \
  --data-urlencode 'page=1' \
  --data-urlencode 'page_size=20'
```

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
        "manager": "zhangsan,lisi",
        "remark": "",
        "dns_str": "",
        "status": "1",
        "domain_type": 0,
        "bk_cloud_id": 0,
        "updater": "zhangsan",
        "update_time": "2026-11-19T10:00:00+08:00"
      }
    ],
    "rowsNum": 1
  }
}
```

`rowsNum` 是满足条件的**记录行数**（一行一个实例），不是域名个数。

---

## 9. 写入操作日志

`PUT /api/v1/dns/oplog`

一次可写入多条。**整批校验**：任意一条不合法，整批都不写入。

**请求体**

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
| `logs[].domain_name` | 是 | 操作域名，需符合域名格式；末尾没有 `.` 自动补全 |
| `logs[].content` | 否 | 变更内容，文本 |
| `logs[].op_time` | 否 | 操作时间，格式 `2006-01-02 15:04:05`；不传取服务当前时间 |
| `logs[].client_ip` | 否 | 客户端 IP；不传取请求来源 IP。传了不做校验，传什么存什么 |

**操作类型 `op_type`**

| 值 | 含义 |
|---|---|
| `CREATE_DOMAIN` | 创建域名 |
| `UPDATE_MANAGER` | 修改负责人 |
| `UPDATE_REMARK` | 修改备注 |
| `UPDATE_IP` | 修改 IP |
| `DELETE_DOMAIN` | 删除域名 |

操作日志需要由调用方主动写入，增删改域名的接口不会自动写日志。

```bash
curl -X PUT 'http://{host}/api/v1/dns/oplog' \
  -H 'Content-Type: application/json' \
  -d '{"logs":[{"operator":"zhangsan","op_type":"DELETE_DOMAIN","domain_name":"mysql.test.db.","content":"delete all records"}]}'
```

**响应**：`rowsNum` 为写入条数。

```json
{ "code": 0, "message": "OK", "data": { "detail": null, "rowsNum": 1 } }
```

**失败示例**（`message` 会列出每条的问题）

```json
{ "code": 10001, "message": "logs[0]: op_type[XXX] invalid\r\n", "data": { "detail": null, "rowsNum": 0 } }
```

---

## 10. 查询域名级别操作日志

`GET /api/v1/dns/oplog/domain`

| 参数 | 必填 | 说明 |
|---|---|---|
| `domain_name` | 是 | 域名，模糊匹配（包含即可）；`%`、`_` 按普通字符处理；不会自动补末尾的 `.` |
| `operator` | 否 | 操作人，精确匹配 |
| `op_type` | 否 | 操作类型，传了但不在上表内会报错 |
| `start_time` | 否 | 起始时间（含），格式 `2006-01-02 15:04:05` |
| `end_time` | 否 | 结束时间（含），格式同上 |
| `page`、`page_size` | 否 | 分页，见通用说明 |

```bash
curl -G 'http://{host}/api/v1/dns/oplog/domain' \
  --data-urlencode 'domain_name=mysql.test' \
  --data-urlencode 'start_time=2026-11-01 00:00:00' \
  --data-urlencode 'end_time=2026-11-19 23:59:59'
```

## 11. 查询全局操作日志

`GET /api/v1/dns/oplog/all`

参数与接口 10 相同，区别是**没有** `domain_name`，查询所有域名的日志。

```bash
curl -G 'http://{host}/api/v1/dns/oplog/all' \
  --data-urlencode 'op_type=DELETE_DOMAIN' \
  --data-urlencode 'page=1' \
  --data-urlencode 'page_size=50'
```

**接口 10、11 的响应**（按操作时间倒序，同时间按 `uid` 倒序）

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
        "client_ip": "1.1.1.1",
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

## 12. 查询全部配置

`GET /api/v1/dns/config/all`

无参数，返回 `tb_dns_config` 全部配置项，不分页。

```bash
curl 'http://{host}/api/v1/dns/config/all'
```

```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "detail": [
      {
        "uid": 1,
        "paraname": "last_modified_time",
        "paravalue": "2026-11-19 10:30:00",
        "pararemark": "",
        "update_counter": 12
      }
    ],
    "rowsNum": 1
  }
}
```

其中 `last_modified_time` 在增、删、改实例（接口 1~4）后由服务自动刷新，reload 程序据此判断是否需要重新加载。

## 13. 更新配置项

`POST /api/v1/dns/config`

**请求体**

```json
{ "paraname": "last_modified_time", "paravalue": "2026-11-19 10:30:00", "pararemark": "备注" }
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `paraname` | 是 | 配置名，按它定位记录 |
| `paravalue` | 是 | 配置值 |
| `pararemark` | 否 | 备注。**不传会把备注清空**（按空串写入） |

- 每次更新 `update_counter` 加 1。
- `paraname` 不存在时不报错，`rowsNum` 为 `0`；此接口不会新建配置项。

```bash
curl -X POST 'http://{host}/api/v1/dns/config' \
  -H 'Content-Type: application/json' \
  -d '{"paraname":"last_modified_time","paravalue":"2026-11-19 10:30:00"}'
```
