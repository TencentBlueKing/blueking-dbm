### 描述

集成授权接口，兼容两种情况

- 集群已经迁移到 dbm：
    1. 创建账号
    2. 添加规则
    3. 创建授权单据
- 集群还在 gcs：
    调用 gcs 的 blueking_grant  接口进行授权

### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| client_hosts         | string       | 是     | 客户端主机，如:127.0.0.1 或者 %     |
| db_hosts         | string       | 是     | DB主机（domain#port）     |
| db_name         | string       | 是     | 数据库名     |
| user_name         | string       | 是     | 用户名     |
| password         | string       | 是     | 密码     |
| privileges         | string       | 是     | 权限列表，多个权限以逗号分隔，如:SELECT,INSERT,UPDATE     |


### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
|msg           |string       |错误消息                                |
|job_id           |int       |任务ID                                |
|code           |int       |错误码                                |