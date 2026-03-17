### 描述

查询版本文件列表


### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|



### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |



### 调用示例
```python
curl -X 'GET' \
  'http://example.com/apis/packages/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### 响应示例
```python
{
  "data": {
    "count": 180,
    "next": "http://example.com/apis/packages/?limit=10&offset=10",
    "previous": null,
    "results": [
      {
        "id": 8476,
        "creator": "system",
        "create_at": "2025-11-06T14:47:13+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:47:13+08:00",
        "name": "predixy-1.4.3.tar.gz",
        "version": "Predixy-latest",
        "pkg_type": "predixy",
        "db_type": "redis",
        "path": "/redis/predixy/Predixy-latest/predixy-1.4.3.tar.gz",
        "size": 7871529,
        "md5": "58cd015874538dc6dd5f2669a3de83e0",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 1,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8470,
        "creator": "system",
        "create_at": "2025-11-06T14:47:13+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:47:13+08:00",
        "name": "tendisplus-2.7.3-rocksdb-v8.5.3.tgz",
        "version": "Tendisplus-2.7",
        "pkg_type": "tendisplus",
        "db_type": "redis",
        "path": "/redis/tendisplus/Tendisplus-2.7/tendisplus-2.7.3-rocksdb-v8.5.3.tgz",
        "size": 219967127,
        "md5": "b34d29197772435107d6e10db5cd0c3e",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8509,
        "creator": "system",
        "create_at": "2025-11-06T14:46:54+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:46:54+08:00",
        "name": "bk-dbmon-v0.19.tar.gz",
        "version": "1.0.6",
        "pkg_type": "dbmon",
        "db_type": "redis",
        "path": "/redis/dbmon/1.0.6/bk-dbmon-v0.19.tar.gz",
        "size": 18155745,
        "md5": "43a53b269071c04cec2a194a8d3704ec",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": [],
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8347,
        "creator": "system",
        "create_at": "2025-11-06T14:32:24+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:32:24+08:00",
        "name": "db-remote-service",
        "version": "1.0.3",
        "pkg_type": "cloud-drs",
        "db_type": "cloud",
        "path": "/cloud/cloud-drs/1.0.3/db-remote-service",
        "size": 47170349,
        "md5": "12c376faf9a335f035627fec3df86d63",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8336,
        "creator": "system",
        "create_at": "2025-11-06T14:32:22+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:32:22+08:00",
        "name": "dbha",
        "version": "1.0.3",
        "pkg_type": "cloud-dbha",
        "db_type": "cloud",
        "path": "/cloud/cloud-dbha/1.0.3/dbha",
        "size": 30565823,
        "md5": "c4c6fd9a6167f09e753403c54022a2d4",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8410,
        "creator": "system",
        "create_at": "2025-11-06T14:32:21+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:32:21+08:00",
        "name": "mysql-monitor.tar.gz",
        "version": "1.0.6",
        "pkg_type": "mysql-monitor",
        "db_type": "mysql",
        "path": "/mysql/mysql-monitor/1.0.6/mysql-monitor.tar.gz",
        "size": 9943665,
        "md5": "27af49bfbd4b0ee86aa594cda1bdcf3f",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8401,
        "creator": "system",
        "create_at": "2025-11-06T14:32:21+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:32:21+08:00",
        "name": "mysql-checksum.tar.gz",
        "version": "1.0.6",
        "pkg_type": "mysql-checksum",
        "db_type": "mysql",
        "path": "/mysql/mysql-checksum/1.0.6/mysql-checksum.tar.gz",
        "size": 8241256,
        "md5": "6b99c752cc8ec7c8734eacbd11449463",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8413,
        "creator": "system",
        "create_at": "2025-11-06T14:32:20+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:32:20+08:00",
        "name": "dbbackup-go-community.tar.gz",
        "version": "1.0.5",
        "pkg_type": "dbbackup",
        "db_type": "mysql",
        "path": "/mysql/dbbackup/1.0.5/dbbackup-go-community.tar.gz",
        "size": 96093631,
        "md5": "edc2282026b889103eee38a133e5de6e",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8196,
        "creator": "system",
        "create_at": "2025-11-06T14:32:20+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:32:20+08:00",
        "name": "bk-dbmon-mg.tar.gz",
        "version": "1.0.2",
        "pkg_type": "dbmon",
        "db_type": "mongodb",
        "path": "/mongodb/dbmon/1.0.2/bk-dbmon-mg.tar.gz",
        "size": 19444361,
        "md5": "b563750ff689fd5d8419db4eeea79cb1",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      },
      {
        "id": 8498,
        "creator": "system",
        "create_at": "2025-11-06T14:32:19+08:00",
        "updater": "system",
        "update_at": "2025-11-06T14:32:19+08:00",
        "name": "dbactuator.exe",
        "version": "1.0.2",
        "pkg_type": "actuator",
        "db_type": "sqlserver",
        "path": "/sqlserver/actuator/1.0.2/dbactuator.exe",
        "size": 23501312,
        "md5": "9284bed85947ca5750e85df36d412256",
        "allow_biz_ids": null,
        "mode": "system",
        "priority": 0,
        "enable": true,
        "permit_os": null,
        "permit_os_type": "",
        "db_version": null
      }
    ]
  },
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "bc508cdba4524fe3becded2f5d8668af"
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| data         | dict       | 响应数据                       |
| count        | int        | 总数量                         |
| next         | string     | 下一页URL                      |
| previous     | string     | 上一页URL                      |
| results      | list       | 结果列表                       |
| id           | int        | 包ID                           |
| creator      | string     | 创建人                         |
| create_at    | string     | 创建时间                       |
| updater      | string     | 更新人                         |
| update_at    | string     | 更新时间                       |
| name         | string     | 包名称                         |
| version      | string     | 版本                           |
| pkg_type     | string     | 包类型                         |
| db_type      | string     | 数据库类型                     |
| path         | string     | 包路径                         |
| size         | int        | 包大小                         |
| md5          | string     | MD5校验值                      |
| allow_biz_ids| list       | 允许的业务ID列表               |
| mode         | string     | 模式                           |
| priority     | int        | 优先级                         |
| enable       | bool       | 是否启用                       |
| permit_os    | list       | 允许的操作系统列表             |
| permit_os_type| string     | 允许的操作系统类型             |
| db_version   | string     | 数据库版本                     |
| code         | int        | 响应状态码                     |
| result       | bool       | 响应结果                       |
| message      | string     | 响应消息                       |
| request_id   | string     | 请求ID                         |