### mongodb_data_export
MongoDB 数据导出任务

```bash
./mongo-dbactuator --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="mongodb_data_export" --payload='{{payload_base64}}'
```

## 原始payload

### 使用 mongodump 导出数据

```json
{
  "bk_dbm_instance": {
    "bk_biz_id": 123,
    "bk_cloud_id": 0,
    "cluster_domain": "test.mongodb.cluster",
    "cluster_name": "test-mongodb-cluster",
    "cluster_type": "MongoReplicaSet",
    "instance_role": "mongo_m1",
    "machine_type": "mongodb"
  },
  "ip": "127.0.0.1",
  "port": 27017,
  "adminUsername": "admin",
  "adminPassword": "password123",
  "maxConcurrency": 4,
  "filename": "m1.test-01.dba.db_1760431272",
  "upload_detail": {
    "bk_cloud_id": 0,
    "db_cloud_token": "",
    "fileserver": {
      "url": "http://bkrepo.example.com",
      "bucket": "xxx",
      "password": "xxx",
      "username": "xxx",
      "project": "xxx",
      "upload_path": "mongodb-data-export/0"
    }
  },
  "args": {
    "is_dumping": true,
    "is_partial": false
  },
  "filename": "exported_filename",
  "package_path": "path/to/mongodb-linux-xxx.tar.gz"
}
```

### 使用 mongoexport 导出数据

```json
{
  "ip": "127.0.0.1",
  "port": 27017,
  "adminUsername": "admin",
  "adminPassword": "password123",
  "maxConcurrency": 4,
  "filename": "m1.test-01.dba.db_1760431272",
  "upload_detail": {
    "bk_cloud_id": 0,
    "fileserver": {
      "url": "http://bkrepo.example.com",
      "bucket": "xxx",
      "password": "xxx",
      "username": "xxx",
      "project": "xxx",
      "upload_path": "mongodb-data-export/0"
    }
  },
  "args": {
    "is_dumping": true,
    "is_partial": true,
    "ns_filter": {
      "db_patterns": ["appdata"],
      "ignore_dbs": ["admin", "config", "local"],
      "table_patterns": ["users"],
      "ignore_tables": []
    },
    "query": "{\"age\": {\"$gt\": 12}}",
    "format": "json"
  },
  "filename": "exported_filename",
  "package_path": "path/to/mongodb-linux-xxx.tar.gz"
}
```

## 参数说明

- `bk_dbm_instance`: DBM 实例元数据信息
- `ip`: MongoDB 实例 IP 地址（必填）
- `port`: MongoDB 实例端口（必填）
- `adminUsername`: 管理员用户名（必填）
- `adminPassword`: 管理员密码（必填）
- `maxConcurrency`: 最大并发数，默认为 4
- `filename`: 导出文件名（必填），用于本地和远程文件命名
- `upload_detail`: 上传到制品库的配置信息
  - `bk_cloud_id`: 云区域 ID
  - `db_cloud_token`: 云区域 token
  - `fileserver`: 制品库服务器信息
    - `url`: 制品库地址
    - `project`: 制品库项目
    - `bucket`: 目标 bucket
    - `upload_path`: 上传路径
    - `username`: 制品库用户名
    - `password`: 制品库密码
- `args`: 导出参数
  - `is_dumping`: 是否使用 mongodump（true）或 mongoexport（false）
  - `is_partial`: 是否部分导出
  - `ns_filter`: 命名空间过滤器（部分导出时使用）
    - `db_patterns`: 数据库名称匹配模式列表
    - `ignore_dbs`: 忽略的数据库列表
    - `table_patterns`: 表名称匹配模式列表
    - `ignore_tables`: 忽略的表列表
  - `query`: 查询过滤条件（JSON 字符串格式）
  - `fields`: 导出的字段列表（mongoexport 使用，逗号分隔）
  - `format`: 导出格式，可选 "json" 或 "csv"（mongoexport 使用）
- `filename`: 生成的文件名，比如 m1.test.db_xxxx （域名和时间戳）
- `package_path`: mongodb安装包的路径，用于取得 mongodump 和 mongoexport

## 注意事项

- 该任务不能以 root 用户执行
- 导出文件会自动压缩为 tar 格式
- 导出完成后会自动上传到制品库
- 临时导出目录位于 "dbbak/mongodb-data-export"
- 上传成功后会删除本地导出文件
- 使用 mongodump 时：
  - `is_partial` 为 false 时执行全量导出
  - `is_partial` 为 true 时根据 `ns_filter` 进行部分导出
  - 使用 `query` 参数时必须配合 `is_partial` 和具体的集合
- 使用 mongoexport 时：
  - 必须设置 `is_partial` 为 true
  - `format` 为 "csv" 时必须指定 `fields` 参数
  - `format` 默认为 "json"
- 查询条件必须是有效的 MongoDB 查询文档 JSON 格式
