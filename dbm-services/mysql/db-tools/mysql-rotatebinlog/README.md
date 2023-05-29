
# 开发
## 编译
```
make release VERSION=0.2.10
```

# 使用
## rotate 频率
rotate_binlog 通过 crontab 等定时任务管理器，周期性调起

`flush binary logs` 的频率由 `rotate_interval` 控制，一般它要 >= rotate_binlog运行频率

## 自适应 binlog 目录
会自己判断需要释放多少空间，来满足空间的要求。

多实例的情况下，会进可能保证每个实例的 binlog 总大小接近，从最大的开始删。

多实例的binlog在不同的挂载分区时，会各自根据每个分区的空间大小，来判断每个分区上有哪些 binlog实例。


## 单机多实例 binlog rotate，使用一个进程进行
因为 rotate 需要计算总共释放多少空间来满足 空间使用率 要求，单机多个实例不能完全独立的去rotate，而是需要全局去把控。

所以 config.yaml 配置渲染的时候是多实例配置在一个 配置文件

## purge index
为了避免直接 purge 来直接删除 binlog 可能会导致实例卡主，rotate_binlog 程序是先删 binlog 文件，再 purge 掉已删除的文件，让 purge 来维护 binlog.index 文件。

purge index 的频率由 `purge_interval` 来控制，注意 当 `purge_interval` 小于 rotate 运行周期时，每次都会 purge 。

## 上传备份系统
超过 `max_keep_duration` 时间的 binlog 会直接从本地删除。

目前只有 db_role = master 的实例才会上传 binlog

## 删除某个 binlog 实例的 rotate
```
./rotate_binlog -c config.yaml --removeConfig 20000,20001
```
如果机器上所有实例都被删除，需要外部去停止定时任务。

## 管理schedule
rotate_binlog 可以作为独立程序 crontab 来运行，也可以注册到 mysql-crond 中，由它来定时调度
```
./rotate_binlog -c config.yaml --addSchedule
./rotate_binlog -c config.yaml --delSchedule
```
调度频率，由 config.yaml `crond.schedule` 来定义。

## sqlite
rotate_binlog 通过 sqlite 本地 db 记录处理过的 binlog 状态，代替一起通过文本文件的方式。

## sqlite migrations
为了避免对存量 DB 实例 如果更新了 binlog_rotate sqlite 表结构，避免重建 sqlite 库，会导致已处理的 binlog 混乱，需要手动做 sql migration
如果涉及字段变更，因为 sqlite 不支持 drop column, change column 语法，migrations 里面要重建表，例如：
```
PRAGMA foreign_keys=off;

BEGIN TRANSACTION;

ALTER TABLE binlog_rotate RENAME TO binlog_rotate_old;

CREATE TABLE IF NOT EXISTS binlog_rotate (
    bk_biz_id integer not null,
    cluster_id integer not null,
    cluster_domain varchar(120) default '',
    db_role varchar(20) not null default '',
    host varchar(64) not null,
    port integer default 0,
    filename varchar(64) not null,
    filesize integer not null,
    file_mtime varchar(32) not null,
    start_time varchar(32) default '',
    stop_time varchar(32) default '',
    backup_status integer default -2,
    backup_status_info varchar(120) not null default '',
    task_id varchar(64) default '',
    created_at varchar(32) default '',
    updated_at varchar(32) default '',
    PRIMARY KEY(cluster_id,filename,host,port)
);

CREATE INDEX idx_status
    ON binlog_rotate (backup_status);
    
INSERT INTO binlog_rotate (
  bk_biz_id, cluster_id, db_role,host,port,filename,filesize,file_mtime,start_time,stop_time,backup_status,backup_status_info,task_id,created_at,updated_at
  )
  SELECT 
  bk_biz_id, cluster_id, db_role,host,port,filename,filesize,file_mtime,start_time,stop_time,backup_status,backup_status_info,task_id,created_at,updated_at
  FROM binlog_rotate_old;

DROP TABLE IF EXISTS binlog_rotate_old;

COMMIT;

PRAGMA foreign_keys=on;
```