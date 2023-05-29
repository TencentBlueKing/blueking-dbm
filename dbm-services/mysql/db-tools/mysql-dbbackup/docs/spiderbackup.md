
# dbbackup spiderbackup
## 生成spider备份

在 spider master (即 tdbctl master) 节点运行
```
./dbbackup spiderbackup -c dbbackup.25000.ini schedule
./dbbackup spiderbackup -c dbbackup.25000.ini schedule --wait
./dbbackup spiderbackup -c dbbackup.25000.ini schedule --wait --backup-id=xx-xx-xx
```
会生成一个 uuid 写入 `infodba_schema.global_backup` 表，也可以指定 `--backup-id`。

## 各节点执行备份
```
cd /home/mysql/dbbackup-go/dbbackup && ./dbbackup spiderbackup check --run -c dbbackup.20000.ini,dbbackup.20001.ini
```

会对指定的备份配置文件（没有指定时，在当前目录find dbbackup.*.ini），检查是否有备份任务，如果有则执行备份。
执行备份会以 `infodba_schema`.`global_backup` 表中的 backup uuid 记录备份信息

## 定时任务配置 mysql-crond 

- remote_master, remote_slave, spider_master
```
cd /home/mysql/mysql-crond
./mysql-crond addJob --name spiderbackup-check  -c runtime.yaml \
  --command /home/mysql/dbbackup-go/dbbackup \
  --args spiderbackup,check,--run \
  --work_dir /home/mysql/dbbackup-go \
  --schedule "*/1 * * * *" \
  --creator xxx \
  --enable 
```

如果是  spider_master，将会直接调用 `dbbackup_main.sh` 备份目录下的所有 .ini （包括 tdbctl master的）。
如果是 remote_master, remote_slave，将会调用 `dbbackup dumpbackup` 命令

- spider_master
```
cd /home/mysql/mysql-crond
./mysql-crond addJob --name spiderbackup-schedule  -c runtime.yaml \
  --command /home/mysql/dbbackup-go/dbbackup \
  --args spiderbackup,schedule,-c,dbbackup.25000.ini \
  --work_dir /home/mysql/dbbackup-go \
  --schedule "0 3 * * *" \
  --creator xxx \
  --enable 
```

# spider 全局备份原理
通过在一个 spider 节点上，向备份任务表 infodba_schema.global_backup 写入各节点的备份任务。

为保证每个后端节点能在自身的 global_backup 表里查到自己的备份任务，使用 `shard_value mod num_shard` 来保证每个节点都有任务。

## BackupStatus 状态维护

- init
  任务刚生成的初始状态。目前指定要求 tdbctl master 所在的 spider 节点运行
  会根据 tdbctl tc_is_primary 判断当前节点是否是 spider master。
- running
  备份进行中，会在 TaskPid 字段进程 id信息
- success
  备份成功
- failed
  备份失败。在部分情况会有 `failed: no pid` 标准失败原因
- quit
  可以手动 update 任务状态为 quit，在`check`轮询时发现这个状态的任务，会强制把对应的 TaskPid kill 掉，达到批量终止备份任务的效果

每轮的 `check` 操作会检查 running 状态的任务，如果 TaskPid 不存在，则会标记为 failed 。这在备份过程中实例挂掉后，能够继续维护任务状态流转。

在 spider master 指定 `schedule --wait` 时会同步等待本次任务在其他节点全部结束才退出，如果有任意节点 failed，则 wait exit code=1。
- 在 `--wait` 过程如果 spider master 自身挂掉，并不会马上退出，而是会持续检查，直到尝试 120 次后再退出
- wait 会同时检查 remote slave 上的 global_backup，因为在 spider master node 无法查询到 remote slave 的表，需要从中控节点轮询


`spiderbackup schedule` 时也能指定 `--backup-id` 参数，则不会自动生成 BackupId 而是使用指定值
`spiderbackup check --run` 也能指定 `--backup-id` 参数，表示运行指定 backup-id 的任务。

备份任务是按 机器 + backup-id 来调度的：
1. 比如机器有 4 个实例，一下子接受到 2 个备份任务(2 个backup-id)
2. `spiderbackup check` 会先把本机所有实例 init 状态的任务取出，再按时间排序，取最早的任务对应的 backup-id
3. 再根据这个 backup-id 找到所有需要备份的实例列表，顺序逐个进行备份。逐个备份前会检查当前备份任务的状态是否发生变化
4. 周期性的 `spiderbackup check` 任务发现本机有任一 running 状态的任务，则跳过本轮。 当没有running状态的任务时，则继续第二个 backup-id 任务
5. 单个实例备份失败，不会影响其它实例备份，但整个操作会 exit code=1
6. 周期性 `spiderbackup check` 任务还会处理备份超过 48h 的任务

## 查询备份状态

```
./dbbackup spiderbackup query
./dbbackup spiderbackup query --backupId=xx-xx-xx 
./dbbackup spiderbackup query --backupStatus=running
```