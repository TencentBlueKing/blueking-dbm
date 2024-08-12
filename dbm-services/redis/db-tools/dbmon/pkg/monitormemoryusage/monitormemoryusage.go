// Package monitormemoryusage TODO
package monitormemoryusage

import (
	"os"
	"runtime"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/redisbinlogbackup"
	"dbm-services/redis/db-tools/dbmon/pkg/redisfullbackup"
	"dbm-services/redis/db-tools/dbmon/pkg/redismaxmemory"
	"dbm-services/redis/db-tools/dbmon/util"
)

// MonitorMemoryUsg 检测内存使用情况
func MonitorMemoryUsg() {
	var m runtime.MemStats
	var times int64 = 0
	binlogBackupGlob := redisbinlogbackup.GetGlobRedisBinlogBackupJob(config.GlobalConf)
	fullBackupGlob := redisfullbackup.GetGlobRedisFullCheckJob(config.GlobalConf)
	checkFullBackGlob := redisfullbackup.GetGlobRedisFullCheckJob(config.GlobalConf)
	maxmemoryGlob := redismaxmemory.GetGlobRedisMaxmemorySet(config.GlobalConf)
	for {
		time.Sleep(5 * time.Second)
		times++
		runtime.ReadMemStats(&m)
		// 分配内存超过500M就终止程序,等待crontab自动拉起
		if m.Alloc >= 500*consts.MiByte {
			if binlogBackupGlob.IsRunning || fullBackupGlob.IsRunning ||
				checkFullBackGlob.IsRunning || maxmemoryGlob.IsRunning {
				mylog.Logger.Error("dbmon memory usage %s exceed 500M, but binlogbackup or fullbackup or maxmemory is running",
					util.SizeToHumanStr(int64(m.Alloc)))
				continue
			}
			mylog.Logger.Error("dbmon memory usage %s exceed 500M,now exit", util.SizeToHumanStr(int64(m.Alloc)))
			os.Exit(1)
		}
		// 超过100MB,每隔2分钟秒打印一次内存使用情况
		if m.Alloc >= 100*consts.MiByte && times%24 == 0 {
			mylog.Logger.Error("dbmon memory usage %s exceed 100M", util.SizeToHumanStr(int64(m.Alloc)))
		}
	}
}
