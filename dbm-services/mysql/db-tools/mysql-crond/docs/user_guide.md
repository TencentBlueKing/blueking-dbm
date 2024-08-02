
## 查看本机注册的定时任务
`./mysql-crond list -h`  

示例：
```
./mysql-crond list
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
| ID |                  JobName              |   Schedule    |               Command                | Enable |         NextTime          |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
| -1 | mysql-rotatebinlog                    | */5 * * * *   | /xxx/mysql-rotatebinlog/rotatebinlog | false  | 2024-08-02T18:50:19+08:00 |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
|  5 | mysql-monitor-3306-@every 1m          | @every 1m     | /xxx/mysql-monitor/mysql-monitor     | true   | 2024-08-02T17:59:17+08:00 |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
| 10 | mysql-monitor-3306-hardcode-heartbeat | @every 10s    | /xxx/mysql-monitor/mysql-monitor     | true   | 2024-08-02T17:59:07+08:00 |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
|  9 | mysql-monitor-3306-hardcode-db-up     | @every 10s    | /xxx/mysql-monitor/mysql-monitor     | true   | 2024-08-02T17:59:07+08:00 |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
|  3 | mysql-monitor-3306-0 55 23 * * *      | 0 55 23 * * * | /xxx/mysql-monitor/mysql-monitor     | true   | 2024-08-02T23:55:00+08:00 |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
|  6 | mysql-monitor-3306-0 5 10 * * *       | 0 5 10 * * *  | /xxx/mysql-monitor/mysql-monitor     | true   | 2024-08-03T10:05:00+08:00 |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
| -1 | dbbackup-schedule                     | 3 3 * * *     | /xxx/dbbackup-go/dbbackup_main.sh    | false  | 0001-01-01T00:00:00Z      |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+
|  1 | mysql-checksum-3306                   | 0 5 2 * * 1-5 | /xxx/checksum/mysql-table-checksum   | true   | 2024-08-05T02:05:00+08:00 |
+----+---------------------------------------+---------------+--------------------------------------+--------+---------------------------+

可以加过滤
./mysql-crond list --name-match "mysql-monitor-3306.*"
```
- `--name-match`: 可用正则匹配 JobName
- `Enable` 列为 false，表示暂停调度的任务。此时 Job ID 为-1
  如果 `NextTime` 是有效值(非`0001-01-01T00:00:00Z`)，表示临时暂停，对应的时间后会恢复，不表示下次运行 job的时间。


## 临时暂停调度某个任务
正在运行的任务，不会停止。已经暂停过的任务，不能再次重复暂停。
`./mysql-crond pause-job -h`  

```
暂停 mysql-rotatebinlog 1小时，不不执行 binlog 滚动程序
./mysql-crond pause-job --name mysql-rotatebinlog -r 1h

暂停某个端口的 mysql-monitor 本地监控 10 分钟
./mysql-crond pause-job --name-match mysql-monitor-3306-.* -r 10m

跳过今晚不做全备
./mysql-crond pause-job -n dbbackup-schedule -r 24h
```
达到设定的 duration 之后会自动恢复调度。

## 持续停止调度某个任务
正在运行的任务，不会停止。已经暂停过的任务，不能再次重复暂停。

```
不调度备份程序
./mysql-crond disable-job --name-match "dbbackup-schedule"

重启 mysql-crond 后会从 jobs-config.yaml 恢复任务。如果想持久暂停，需要加 --permanent
```

## 重新启用某个任务
```
pause-job, disable-job 的任务，都可以通过 enable-job 来重新启用
./mysql-crond enable-job --name mysql-rotatebinlog

恢复之前停止的 3306 端口监控
./mysql-crond enable-job --name-match mysql-monitor-3306-.*
```

## 修改任务调度的时间
```
./mysql-crond change-job -h

把备份任务调整到每天 05:03 分执行：
./mysql-crond change-job --name dbbackup-schedule --schedule "3 5 * * *" --permanent
```
不能调整已暂停的任务。