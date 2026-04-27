## mongo-dbactuator
mongo原子任务合集,包含mongo复制集、cluster的创建，备份，回档等等原子任务。

使用方式:
```go
mongo-dbactuator -h
mongo原子任务合集,包含mongo复制集、cluster的创建，备份，回档等等原子任务。

Usage:
  mongo-dbactuator [flags]


Flags:
  -A, --atom-job-list string   多个原子任务名用','分割,如 redis_install,redis_replicaof
  -B, --backup_dir string      备份保存路径,亦可通过环境变量MONGO_BACKUP_DIR指定
      --bin_dir string          Mongo二进制安装根路径,亦可通过环境变量 MONGO_BIN_DIR 指定,默认 /usr/local
  -D, --data_dir string        数据保存路径,亦可通过环境变量 MONGO_DATA_DIR 指定
  -h, --help                   help for mongo-dbactuator
  -N, --node_id string         节点id
  -p, --payload string         原子任务参数信息,base64包裹
  -f, --payload_file string    原子任务参数信息,json/yaml文件
  -R, --root_id string         流程id
  -t, --toggle                 Help message for toggle
  -U, --uid string             单据id
  -V, --version_id string      运行版本id
  -u, --user string            db进程运行的os用户
  -g, --group string           db进程运行的os用户的属主

//执行示例
mongo-dbactuator --uid=1111 --root_id=2222 --node_id=3333 --version_id=v1 --payload='' --atom-job-list="mongod_install"
```

说明:
- `--bin_dir`/`MONGO_BIN_DIR` 主要用于测试环境覆盖 Mongo 二进制安装根路径；线上默认使用 `/usr/local`。
- e2e 脚本中的 `/data2` 仅为测试默认值，线上请按实际磁盘规划使用（常见为 `/data1` 或 `/data`）。
