### Description

MySQL SQL file upload

### Input Parameters  
You can choose one of three methods—`sql_content`, `sql_filenames`, or `sql_files`—for uploading.  

| Parameter Name | Parameter Type | Required | Description |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id | string | Yes | The `{bk_biz_id}` in the path, which is the business ID |
| sql_content | string | No | SQL content |
| sql_filenames | list(string) | No | List of SQL file names, applicable when files have been uploaded to the artifact repository in advance |
| sql_files | list(file) | No | List of SQL file objects |
| cluster_type | string | No | Cluster type |
| versions | list(string) | No | Version list |

### Call Example
```json
{
  "sql_content": "select * from user where user.id = 1",
  "sql_file": null
}
```

### Response Example
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

### Response Parameter Description
| Parameter Name | Parameter Type | Description |
| ------------ | ---------- | ------------------------------ |
| data | dict | Response data dictionary |
| code | integer | Response status code |
| message | string | Response message |
| request_id | string | Request ID |

#### data  
The key of the dictionary will be the file name uploaded to the artifact repository, such as `uZUBqF8_dbmrpt_t.sql` in the response example.  
If the uploaded file has an original file name, a random suffix will be generated on the original file name to avoid overwriting.  

| Parameter Name | Parameter Type | Description |
| ------------ | ---------- | ------------------------------ |
| syntax_fails | string | Syntax errors |
| highrisk_warnings | string | High-risk statement warnings |
| bancommand_warnings | string | Forbidden command warnings |
| content | string | SQL file content |
| sql_path | string | Relative file path of the SQL file in the artifact repository |
| raw_file_name | string | Original SQL file name |
| skip_check | string | Check skipped |