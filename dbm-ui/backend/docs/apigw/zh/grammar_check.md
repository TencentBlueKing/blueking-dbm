### 描述

MySQL SQL文件上传

### 输入参数
可以从sql_content/sql_filenames/sql_files三种方法中选一种进行上传
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
|  bk_biz_id | string | 是 | 路径中的{bk_biz_id}，为业务ID
|  sql_content        | string       | 否     | SQL内容     |
|  sql_filenames        | list(string)       | 否     | sql文件名列表，适用于已经提前把文件上传到制品库     |
|  sql_files        | list(file)       | 否     | sql文件对象列表      |
|  cluster_type        | string       | 否     | 集群类型     |
|  versions        | list(string)     | 否     | 版本列表     |

### 调用示例
```json
{
  "sql_content": "select * from user where user.id = 1",
  "sql_file": null
}
```

### 响应示例
```json
{
  "data": {
    "uZUBqF8_dbmrpt_t.sql": {
      "syntax_fails": "",
      "highrisk_warnings": "",
      "bancommand_warnings": "",
      "content": "select * from user where user.id = 1",
      "sql_path": "mysql/sqlfile/100706/uZUBqF8_dbmrpt_t.sql",
      "raw_file_name": "t.sql",
      "skip_check": ""
    }
  },
  "code": 0,
  "message": "OK",
  "request_id": "12616947f890e0ea18dc8a2d8ea15db9"
}

```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
|  data            |  dict          |  响应数据字典                              |
|  code            |  integer          |  响应状态码                              |
|  message            | string           |  响应信息                              |
|  request_id            | string           |  请求ID                              |
#### data
会以上传到制品库的文件名作为字典的key，如响应示例中的uZUBqF8_dbmrpt_t.sql
如果上传文件有原始文件名，为了避免文件覆盖，会在原来的文件名上随机生成后缀区分。
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
|  syntax_fails            | string           |   语法错误                             |
|  highrisk_warnings            | string           |   高风险语句警告                             |
|  bancommand_warnings            | string           |  禁止指令警告                              |
|  content            | string           |   sql文件内容                             |
|  sql_path            |  string          |  sql文件在制品库里的相对文件路径                              |
|  raw_file_name            |  string          |  原始sql文件名                              |
|  skip_check            |  string          |     检查跳过                           |