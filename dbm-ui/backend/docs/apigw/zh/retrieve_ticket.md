### 功能描述

创建单据

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号

### 请求参数

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| id | int | 是 | 单据ID |


### 请求参数示例

```shell
curl -H 'X-Bkapi-Authorization: {"access_token": "your_token"}' "https://bkdbm.apigw.example.com/prod/tickets/238/"
```

### 返回结果示例

```json
{
    "id": 1138,
    "creator": "admin",
    "create_at": "2023-10-20T22:17:01+08:00",
    "updater": "admin",
    "update_at": "2023-10-20T22:17:34+08:00",
    "ticket_type": "MYSQL_HA_FULL_BACKUP",
    "status": "SUCCEEDED",
    "remark": "bksops-full backup of MySQL database tables",
    "group": "mysql",
    "details": {"...": "..."},
    "ticket_type_display": "MySQL 高可用全库备份",
    "status_display": "成功",
    "cost_time": 32,
    "bk_biz_name": "DBA",
    "db_app_abbr": "dba",
    "ignore_duplication": false,
    "send_msg_config": {},
    "bk_biz_id": 3,
    "is_reviewed": false
}
```

### 返回结果参数说明

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| id | int | 是 | 单据ID |
| creator | string | 是 | 单据创建者 |
| create_at | string | 是 | 单据创建时间 |
| updater | string | 是 | 单据更新者 |
| update_at | string | 是 | 单据更新时间 |
| ticket_type | string | 是 | 单据类型 |
| status | string | 是 | 单据状态 |
| remark | string | 是 | 单据备注 |
| group | string | 是 | 单据所属组 |
| details | dict | 是 | 单据差异化参数，详见单据类型的details定义 |
| ticket_type_display | string | 是 | 单据类型展示名 |
| status_display | string | 是 | 单据状态展示名 |
| cost_time | int | 是 | 单据流转时间 |
| bk_biz_name | string | 是 | 业务名 |
| db_app_abbr | string | 是 | 业务英文名 |
| ignore_duplication | string | 否 | 是否忽略单据重复提交 |
| send_msg_config | dict | 否 | 单据通知配置 |
| bk_biz_id | string | 是 | 单据ID |
| is_reviewed | bool | 是 | 单据是否已被review |

#### 单据状态枚举定义
```python
("PENDING", _("等待中"))
("RUNNING", _("执行中"))
("SUCCEEDED", _("成功"))
("FAILED", _("失败"))
("REVOKED", _("撤销"))
("TERMINATED", _("终止"))
```