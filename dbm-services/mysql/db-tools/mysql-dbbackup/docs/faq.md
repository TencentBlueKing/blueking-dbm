### 1. 怎么改备份类型：物理备份、逻辑备份
**如果是永久修改，则修改配置文件** 
```
[Public]
BackupType      =       logical
```
BackupType 可选值：`logical`, `physical`, `auto`
`auto` 表示自动选择备份类型，自动判断条件：
 - 当机器 glibc 版本 < 2.14 (centos 6.x)，`physical`
 - 当数据目录的数据量 > 400G 时，`physical`
 - 当机器 glibc 版本 >=2.14 且数据量小于 400G，`logical`

**如果是临时发起一次逻辑备份**
可不用修改配置文件
```
./dbbackup dumpbackup -c dbbackup.3306.ini --backup-type logical
```

### 2. 怎么修改备份内容：表结构、数据
```
[Public]
DataSchemaGrant = all
```
可选值有 `all`, `schema`, `data`, `grant`， 也可以组合使用 `schema,grant`, `all` 相当于别称`schema,data,grant`

### 3. 备份空间不足，但人为评估磁盘应该能放得下
如果评估压缩率比较高，或者空洞率比较高，逻辑备份空间够用，可发起一次备份加上选项 `--nocheck-diskspace`
```
./dbbackup dumpbackup -c dbbackup.3306.ini --backup-type logical  --nocheck-diskspace
```
每次备份之后，都会往 `infodba_schema.local_backup_report` 里记录一条备份信息，下一次备份时遇到空间不足，会从这里读取上次备份的文件大小来判断空间。
不建议将 `Public.NoCheckDiskSpace` 持久化到配置文件

### 4. 怎么修改备份开始时间

- **tendbha主从高可用集群**  
进入 mysql-crond 任务调度程序目录
```
cd /home/mysql/mysql-crond
./mysql-crond  list
```

修改 schedule:
```
 ./mysql-crond change-job --permanent -n "dbbackup-schedule" --schedule "4 3 * * *"
```
某些旧版本的 mysql-crond 没有 change-job命令，可以直接修改 `jobs-config.yaml`，再重启 mysql-crond
```
    - name: dbbackup-schedule
      enable: true
      command: /home/mysql/dbbackup-go/dbbackup_main.sh
      args:
        - '>'
        - /home/mysql/dbbackup-go/logs/main.log
        - 2>&1
      schedule: 3 3 * * *
      creator: system
      work_dir: /home/mysql/dbbackup-go
```

- **tendbcluster 集群**  
spider 集群的备份由两个任务组成
  - `spiderbackup-schedule`  
   发起备份，即调度起一个 backup-id 的备份，会向 spider, remote master 写入备份任务`infodba_schema.global_backup`。
   remote slave 的任务由 remote master 同步过来，如果有主从延迟，可能不会马上在 slave 上看到备份进程
  - `spiderbackup-check`  
   每分钟轮训判断本机是否有备份任务，如果有则执行备份

修改备份时间时间 schedule：
```
./mysql-crond change-job --permanent -n "spiderbackup-schedule" --schedule "4 3 * * *"
```

-- **也可直接修改jobs-config.yaml**  
某些旧版本的 mysql-crond 没有 change-job 命令，可以直接修改 `jobs-config.yaml`，再重启 mysql-crond
```
    - name: spiderbackup-schedule
      enable: true
      command: /home/mysql/dbbackup-go/dbbackup
      args:
        - spiderbackup
        - schedule
        - --config
        - dbbackup.25000.ini
      schedule: 3 3 * * *  --- 改这个
      creator: xxx
      work_dir: /home/mysql/dbbackup-go
```

如果需要重启 mysql-crond  
```
./stop.sh && sleep 1
./start.sh
```


### 5. 怎么手工在机器上发起备份
首先要坚持当前实例的角色，比如备份类型(physical/logical)，备份角色(master/slave)，备份内容(all/schema,grant)

- **主从集群**
```
cd dbbackup-go

# 默认生成一个随机 backup uuid，遍历目录下的 dbbackup.<port>.ini 顺序执行
./dbbackup_main.sh

# 也可以直接调用二进制
./dbbackup dumpbackup -c dbbackup.3306.ini
# 指定 backup_id 等选项，--backup-id xx-xx-xx --backup-type physical -g all
./dbbackup dumpbackup -c dbbackup.3306.ini
```

- **tendbcluster集群**
在 spider primary 节点(即中控 tdbctl primary)，发起全局备份(共用一个 backup_id):

```
异步发起备份
./dbbackup spiderbackup -c dbbackup.25000.ini schedule
查看备份进度
./dbbackup spiderbackup query --backupId=xx-xx-xx 

同步等备份完成
./dbbackup spiderbackup -c dbbackup.25000.ini schedule --wait
```

当然也可以想主从集群那样，在单个分片上发起自己的备份。

### 6. 怎么调整磁盘 io 限速
限速分为 2 个阶段：导出阶段，打包切分阶段

导出阶段:
```
logical 暂时不支持导出限速

physical 可设置 PhysicalBackup.Throttle, 单位是每秒拷贝 chunk 数量，一个 chunk 10MB。但总速度得结合 Threads 来设置
[PhysicalBackup]
Throttle = 200
Threads = 2
```

打包切分阶段：
```
物理备份、逻辑备份的打包切分，都受到 Public.IOLimitMBPerSec 控制，单位 MB/s
[Public]
IOLimitMBPerSec = 300
```
参数 `Public.IOLimitMasterFactor = 0.5` 可进一步限制在 master 上备份的限速，表示的是限速因子，比如 0.5 表示实际限速为 `IOLimitMBPerSec * 0.5`, `Throttle * 0.5`

### 7. 关于逻辑备份字符集说明
首先，mysql 的表结构上的 comment 注释，mysqld 内部都是以 utf8 来编码的，它与表结构定义的 charset 和 表里面数据的字符集 都么有关系。mysqldump 导出表结构时，可以看到都设置为了 utf8，能正确处理。

mydumper 的处理比较粗暴，表结构，表数据 都是以指定的 `--set-names` 来导出，并且把指定的这个字符集写到导出结果文件里。

所以不论是 mysqldump 还是 mydumper，数据恢复回去时，都可以不用指定字符集。

对于备份来说，指定逻辑备份的字符集选项 `Public.MysqlCharset`，留空时会读取 mysqld `character_set_server`，效果等同于 `Public.MysqlCharset=auto`。

也可以指定为具体的字符集，但最好与表写入的字符集或者定义的字符集相同，否则导出数据可能错乱。也可以指定为 binary，但这也要求表定义的 comment上没有一些乱码等不可识别的字符，否则结果无法导入（数据可以导入）。

### 8. 如何只备份表结构用于重做从库
`Public.IsFullBackup` or `--is-full-backup` 这个选项默认 0 代表会自动根据备份方式+备份对象 来决定是否将备份上报为全备

某些情况只需要表结构，可以设置此选项强制上报为全备
```
./dbbackup dumpbackup -c dbbackup.3306.ini --is-full-backup 1 \
 --data-schema-grant schema,grant \
 --backup-type logical
```

### 9. 关于 tendbcluster 集群备份，请参考 [spider](spiderbackup.md)

### 10. 关于如何重新上报备份记录
每一次备份都会将备份信息写入 `dbareport/mysql/dbbackup/backup_result.log`，记录会实时被蓝鲸日志采集上报。
如果想覆盖某条备份记录，可以从中找出相应的 backup_id 后，根据需要修改对应字段，再重新写一条进去。
```
-- 找到需要重新上报的 backup_id，比如 xxx-xxx-xxx
grep xxx-xxx-xxx ~/dbareport/mysql/dbbackup/backup_result.log > /data/dbbak/xxx-xxx-xxx.backup_result.log

-- 根据需要修改

-- 写回去(追加)
cat /data/dbbak/xxx-xxx-xxx.backup_result.log >> ~/dbareport/mysql/dbbackup/backup_result.log
```

### 19. 常见备份失败处理

#### 1. log copying being too slow
> it looks like InnoDB log has wrapped around before xtrabackup could process all records due to either log copying being too slow, or  log files being too small.

实例写入速度比备份速度快，可能是刚刚备份时间段有大批量 DML 操作，修改备份开始时间，或者加快备份速度: 

调大 PhysicalBackup.Throttle, 调大 PhysicalBackup.Threads

#### 2. mydumper 不支持 centos 6.x
> mydumper: error while loading shared libraries: libpcre.so
> 
> /lib64/libc.so.6: version `GLIBC_2.14' not found (required by xxx)

mydumper / myloader 依赖 glibc>=2.14, centos 6.x(or tlinux 1.2) 是 glibc 2.12，可能会报如上错误。查看 glibc 版本`ldd --version |grep libc`。

如果必须使用逻辑备份，可以设置 `UseMysqldump = auto` 则会在 mydumper 不可用时，自动选择 mysqldump 进行备份
```
[LogicalBackup]
UseMysqldump = auto
Databases = *
Tables = *

[Public]
BackupType = logical
```
使用 mysqldump 备份 slave 数据，会短暂停止同步 sql thread来获取一致性 binlog 位点，可能会触发告警。备份结束(成功/失败)会自动恢复 sql thread（非 kill 掉的情况）

#### 3. xtrabackup 8.0 不支持 centos 6.x
> xtrabackup: error while loading shared libraries: libsystemd.so.0: cannot open shared object file: No such file or directory
>
> /usr/lib64/libstdc++.so.6: version `GLIBCXX_3.4.15' not found (required by xxx)

mysql 8.0 的物理备份工具 xtrabackup 也依赖 glibc>=2.14 版本，可能会看到如上报错。

#### 4. There are queries in PROCESSLIST running longer than xx
> ** (mydumper:27337): CRITICAL **: 15:01:07.879: There are queries in PROCESSLIST running longer than 120s, aborting dump,
use --long-query-guard to change the guard value, kill queries (--kill-long-queries) or use different server for dump

mydumper 备份发起的时候，当前实例有运行超过 120s的慢查询（`--long-query-guard=120`），在经历时间 `--long-query-retry-interval`\*`--long-query-retries` 之后慢查询还没结束，所以备份退出。

处理方法：
- 如果想自动 kill 掉这类长 sql，可以设置 `Public.KillLongQueryTime=120`，即超过 120s 的 sql会杀掉。
- 如果不想 kill，仅仅想设置更长的时间等待长 sql执行完成，可以设置 `Public.FtwrlWaitTimeout=3600`。
- 调整备份时间段

> ** (mydumper:11132): CRITICAL **: 15:25:09.638: Flush tables failed, we are continuing anyways: Lock wait timeout exceeded; try restarting transaction

mydumper 备份发起的时候，检测到长 sql 执行中（但还没超过`--long-query-guard=120`）,mydumper 会立即发出 FLUSH TABLE 操作，等待慢查询结束，默认等待 10s 之后 flush table 获取所锁失败，退出看到以上错误信息。

`FLUSH NO_WRITE_TO_BINLOG TABLES` 或者 `FLUSH TABLE WITH READ LOCK` 被锁住，如果有其它读写请求则会被全部阻塞住。

处理方法;
- 可通过调整 `Public.AcquireLockWaitTimeout` 来调整 mydumper `--lock-wait-timeout` 值。
- 调整备份时间段