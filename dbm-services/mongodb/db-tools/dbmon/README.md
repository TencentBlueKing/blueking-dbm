### bk-dbmon
本地例行任务集合,含例行全备、binlog备份、心跳等例行任务。

#### 使用示例
- **配置示例,文件名: dbmon-config.yaml**
```yaml
report_save_dir: /home/mysql/dbareport/
report_left_day: 15
backup_client_storage_type: ""
http_address: 127.0.0.1:6677
bkmonitorbeat:
  agent_address: /usr/local/gse_bkte/agent/data/ipc.state.report
  beat_path: /usr/local/gse_bkte/plugins/bin/bkmonitorbeat
  event_config:
    data_id: 1572877
    token: 91049f4d2cb74881bcef201ebb7302fe
  metric_config:
    data_id: 1572876
    token: 122a95858b174a908a2ab5f7443d546a

servers:
  - bk_biz_id: "3"
    username: root
    password: root
    bk_cloud_id: 0
    app: dba
    app_name: DBA业务
    cluster_domain: m1.test.dba.db
    cluster_id: "12345"
    cluster_name: test1
    cluster_type: ReplicaSet
    role_type: shardsvr
    meta_role: backup
    server_ip: 127.0.0.1
    server_port: 27030
    setname: set1   

```

- **启动**
```sh
./bk-dbmon-mg --config=dbmon-config.yaml
```
- **调试**
```sh
./bk-dbmon debug sendmsg   --config ./bk-dbmon-config.yaml  --port 27001 --type event --msg "test msg"
./bk-dbmon debug sendmsg   --config ./bk-dbmon-config.yaml  --port 27001 --type ts
```
#### 架构
