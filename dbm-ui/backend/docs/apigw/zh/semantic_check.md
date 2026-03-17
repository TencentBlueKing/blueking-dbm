### 描述

MySQL 语义执行

### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
|  bk_biz_id | string | 是 | 路径中的{bk_biz_id}，为业务ID
|  cluster_ids| list(int)       | 是     | 集群id列表     |
|  ticket_type        | string       | 是     |  语义检查类型    |
|  charset        | string       | 是     | 字符集      |
|  execute_objects        | list(dict)       | 是     | 执行对象     |
|  ticket_mode        | dict     | 是     | 执行模式     |
|  backup        | list(dict)     | 是     | 执行前备份     |
|  cluster_type        | dict     | 是     | 集群类型     |
|  is_auto_commit        | bool     | 是     | 是否自动提单     |

### 调用示例
```json
{
    "bk_biz_id": 100706,
    "cluster_ids": [21001790],
    "ticket_type":
        "MYSQL_SEMANTIC_CHECK",
    "charset": "utf8",
    "execute_objects": [
        {"sql_files": ["OYvOW7M_dbmrpt_t.sql"], "ignore_dbnames": ["b"], "dbnames": ["a"], "import_mode": "file"}],
    "ticket_mode": {"mode": "manual", "trigger_time": ""}, 
    "backup": [], 
    "cluster_type": "mysql", 
    "is_auto_commit": False
}
```

### 响应示例
```json
{"result": True, 
 "message": 'ok', 
 "data": {'root_id': 'c4181e0e950711'}
 }

```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
|  data            |  dict          |  响应数据字典                              |
|  result            |  bool          |  响应结果                              |
|  message            | string           |  响应信息                              |
#### data

| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
|  root_id            | string           |   root_id                             |