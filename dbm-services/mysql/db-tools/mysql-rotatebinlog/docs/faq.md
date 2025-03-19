## 1. binlog 清理逻辑是怎样的?

binlog 目录还有很多空间，怎么 binlog 就被清理了？
binlog 目录空间很紧张了，怎么还没被清理？

binlog 清理首先由 `max_binlog_total_size`, `max_disk_used_pct`,`keep_policy` 三个配置决定。

```
public:
  keep_policy: most
  max_binlog_total_size: 2000g
  max_disk_used_pct: 80
```

- keep_policy  
  `least`: 尽可能去清理，但如果是 master 机器，也只会清理已上传的 binlog
  `most`: 尽可能保留binlog，保留影响因素 `max_binlog_total_size`, `max_disk_used_pct`

- max_binlog_total_size  
  binlog 最大允许占用的空间大小。如果是单机多实例，控制的是每个实例的 binlog 目录大小。
  超过这个大小，会强制清理，不论是否需要上传

- max_disk_used_pct  
  binlog 所在分区的最大空间使用率
  注意这里是分区使用率，不是 binlog 目录占分区的使用率。如果 binlog 所在分区存在其他文件(如 /data/dbbak )，也包含在内

还有一个因素：备份程序。例行备份程序，会在备份开始时评估备份所需要的空间，如果删除了历史备份，空间依然不够不够，则会调用 `rotatebinlog clean-space` 命令来释放 binlog 空间， 这种情况当前默认会尝试直接把空间释放到 20%。
```
cleanBinlogCmd := []string{"./rotatebinlog", "clean-space", "--max-disk-used-pct", "20"}

--size-to-free
--max-binlog-total-size
```

在单机多实例场景，rotatebinlog 程序会尽可能公平的保持每个实例所占用 binlog 目录大小接近，所以会优先清理占用大的实例。

## 2. 本地 binlog 目录下的文件不连续了?

binlog 清理机制会优先清理已经上传成功的,最旧的文件，由于上传是调用 backup_client 异步进行的，提交上传任务有可能是批量的。这就导致如果产生的 binlog 比上传 binlog 的速度大，后产生的 binlog 先上传成功，在空间不足触发清理。

可以通过 query 命令查看 binlog 文件的上传状态
```
./rotatebinlog query --filename-like 'binlog.04757%'
```

## 3. 怎么控制 binlog 是否上传备份系统
由 main.yaml 里面的 `backup_enable` 和 server.xxx.yaml 里面的 `db_role` 来决定是否上传备份系统。

- backup_enable=auto 
  `auto` 是默认值，此时只有 db_role=`master` 的实例才会上传 binlog，其他角色如`repeater`,`slave`,`orphan` 默认不上传。

- backup_enable=yes
  此时不论 db_role 值是什么，都会上传备份系统。
  在单节点 mysql 上，db_role=orphan，默认是不上传 binlog的，如果需要上传则设置 `public.backup_enable` 为 `yes`。

首次开启 binlog 上传，当前默认只处理最近 7 天的 binlog。超过 7 天的避免集中大量上传，可以通过 `public.max_old_days_to_upload` 修改。

main.yaml:
```
public:
  backup_enable: auto
  max_old_days_to_upload: 7
```

server.3306.yaml:
```
host: x.x.x.x
port: 3306
username: testuser
password: testpass
tags:
  bk_biz_id: 1234
  cluster_domain: abcd.efg.dbatest.db
  cluster_id: 5678
  db_role: slave
```
