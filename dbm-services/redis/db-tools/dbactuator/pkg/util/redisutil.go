package util

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"

	"github.com/shirou/gopsutil/v3/mem"
)

// GetTendisplusBlockcache 返回单位Mbyte
// 如果系统内存小于4GB,则 instBlockcache = 系统总内存 * 0.3 / 实例数
// 否则 instBlockcache = 系统总内存 * 0.5 / 实例数
func GetTendisplusBlockcache(instCount uint64) (instBlockcache uint64, err error) {
	if instCount <= 0 {
		err = fmt.Errorf("instCount==%d <=0", instCount)
		return
	}
	var vMem *mem.VirtualMemoryStat
	vMem, err = mem.VirtualMemory()
	if err != nil {
		err = fmt.Errorf("mem.VirtualMemory fail,err:%v", err)
		return
	}
	if vMem.Total < 4*consts.GiByte {
		instBlockcache = vMem.Total * 3 / (10 * instCount)
	} else {
		instBlockcache = vMem.Total * 5 / (10 * instCount)
	}
	if instBlockcache < 128*consts.MiByte {
		instBlockcache = 128 * consts.MiByte
	}
	instBlockcache = instBlockcache / consts.MiByte
	return
}

// GetTendisplusWriteBufferSize 返回单位是Byte
// 如果系统内存小于8GB,则 writeBufferSize = 8MB,否则 writeBufferSize = 32MB
func GetTendisplusWriteBufferSize(instCount uint64) (writeBufferSize uint64, err error) {
	if instCount <= 0 {
		err = fmt.Errorf("instCount==%d <=0", instCount)
		return
	}
	var vMem *mem.VirtualMemoryStat
	vMem, err = mem.VirtualMemory()
	if err != nil {
		err = fmt.Errorf("mem.VirtualMemory fail,err:%v", err)
		return
	}
	if vMem.Total <= 8*consts.GiByte {
		writeBufferSize = 8 * consts.MiByte
	} else {
		writeBufferSize = 32 * consts.MiByte
	}
	return
}

// StopBkDbmon 停止bk-dbmon
func StopBkDbmon() (err error) {
	if FileExists(consts.BkDbmonBin) {
		stopScript := filepath.Join(consts.BkDbmonPath, "stop.sh")
		stopCmd := fmt.Sprintf("su %s -c '%s'", consts.MysqlAaccount, "sh "+stopScript)
		mylog.Logger.Info(stopCmd)
		_, err = RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", "sh " + stopScript},
			"", nil, 1*time.Minute)
		return
	}
	mylog.Logger.Info(fmt.Sprintf("bk-dbmon not exists"))
	killCmd := `
pid=$(ps aux|grep 'bk-dbmon --config'|grep -v dbactuator|grep -v grep|awk '{print $2}')
if [[ -n $pid ]]
then
kill $pid
fi
`
	mylog.Logger.Info(killCmd)
	_, err = RunBashCmd(killCmd, "", nil, 1*time.Minute)
	return
}

// StartBkDbmon start local bk-dbmon
func StartBkDbmon() (err error) {
	startScript := filepath.Join(consts.BkDbmonPath, "start.sh")
	if !FileExists(startScript) {
		err = fmt.Errorf("%s not exists", startScript)
		mylog.Logger.Error(err.Error())
		return
	}
	startCmd := fmt.Sprintf("su %s -c 'nohup %s &'", consts.MysqlAaccount, "sh "+startScript)
	mylog.Logger.Info(startCmd)
	_, err = RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", "nohup sh " + startScript + " &"},
		"", nil, 1*time.Minute)

	if err != nil && strings.Contains(err.Error(), "no crontab for") {
		return nil
	}

	return
}

// GetRedisDbTypeByPkgName 根据包名推断 dbtype
func GetRedisDbTypeByPkgName(pkgName string) (dbType string) {
	if strings.Contains(pkgName, "tendisplus") {
		dbType = consts.TendisTypeTendisplusInsance
	} else if strings.Contains(pkgName, "2.8.17") && strings.Contains(pkgName, "-rocksdb-") {
		dbType = consts.TendisTypeTendisSSDInsance
	} else {
		dbType = consts.TendisTypeRedisInstance
	}
	return
}

// ClearBackupClientDir TODO
func ClearBackupClientDir() (err error) {
	stmDir := "/data/backup_stm"
	if FileExists(stmDir) {
		cmd := fmt.Sprintf("rm -rf %s", stmDir)
		mylog.Logger.Info(cmd)
		_, err = RunBashCmd(cmd, "", nil, 1*time.Minute)
		if err != nil {
			mylog.Logger.Error(err.Error())
			return
		}
	}
	if FileExists(consts.COSInfoFile) {
		cmd := fmt.Sprintf("rm -rf %s", consts.COSInfoFile)
		mylog.Logger.Info(cmd)
		_, err = RunBashCmd(cmd, "", nil, 1*time.Minute)
		if err != nil {
			mylog.Logger.Error(err.Error())
			return
		}
	}
	return nil
}

// ClearUsrLocalRedis TODO
func ClearUsrLocalRedis(clearTarget bool) (err error) {
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	if !FileExists(redisSoftLink) {
		// 如果 /usr/local/redis 不存在,则不需要清理
		return nil
	}
	realLink, err := os.Readlink(redisSoftLink)
	// 无论/usr/local/redis是好连接 还是 坏连接
	// 都清理 /usr/local/redis
	rmCmd := fmt.Sprintf("rm -rf %s", redisSoftLink)
	mylog.Logger.Info(rmCmd)
	_, err = RunBashCmd(rmCmd, "", nil, 1*time.Minute)
	if err != nil {
		mylog.Logger.Error(err.Error())
		return
	}
	if err == nil && realLink != "" && FileExists(realLink) && clearTarget {
		// 如果 /usr/local/redis 是一个好的软连接,则清理 连接指向的目标目录
		rmCmd := fmt.Sprintf("rm -rf %s", realLink)
		mylog.Logger.Info(rmCmd)
		_, err = RunBashCmd(rmCmd, "", nil, 1*time.Minute)
		if err != nil {
			mylog.Logger.Error(err.Error())
			return
		}
	}
	return nil
}

// ClearUsrLocalTwemproxy TODO
func ClearUsrLocalTwemproxy(clearTarget bool) (err error) {
	twemproxySoftLink := filepath.Join(consts.UsrLocal, "twemproxy")
	if !FileExists(twemproxySoftLink) {
		// 如果 /usr/local/twemproxy 不存在,则不需要清理
		return nil
	}
	realLink, err := os.Readlink(twemproxySoftLink)
	// 无论/usr/local/twemproxy是好连接 还是 坏连接
	// 都清理 /usr/local/twemproxy
	rmCmd := fmt.Sprintf("rm -rf %s", twemproxySoftLink)
	mylog.Logger.Info(rmCmd)
	_, err = RunBashCmd(rmCmd, "", nil, 1*time.Minute)
	if err != nil {
		mylog.Logger.Error(err.Error())
		return
	}
	if err == nil && realLink != "" && FileExists(realLink) && clearTarget {
		// 如果 /usr/local/twemproxy 是一个好的软连接,则清理 连接指向的目标目录
		rmCmd := fmt.Sprintf("rm -rf %s", realLink)
		mylog.Logger.Info(rmCmd)
		_, err = RunBashCmd(rmCmd, "", nil, 1*time.Minute)
		if err != nil {
			mylog.Logger.Error(err.Error())
			return
		}
	}
	return nil
}

// ClearUsrLocalPredixy TODO
func ClearUsrLocalPredixy(clearTarget bool) (err error) {
	predixySoftLink := filepath.Join(consts.UsrLocal, "predixy")
	if !FileExists(predixySoftLink) {
		// 如果 /usr/local/predixy 不存在,则不需要清理
		return nil
	}
	realLink, err := os.Readlink(predixySoftLink)
	// 无论/usr/local/predixy是好连接 还是 坏连接
	// 都清理 /usr/local/predixy
	rmCmd := fmt.Sprintf("rm -rf %s", predixySoftLink)
	mylog.Logger.Info(rmCmd)
	_, err = RunBashCmd(rmCmd, "", nil, 1*time.Minute)
	if err != nil {
		mylog.Logger.Error(err.Error())
		return
	}
	if err == nil && realLink != "" && FileExists(realLink) && clearTarget {
		// 如果 /usr/local/predixy 是一个好的软连接,则清理 连接指向的目标目录
		rmCmd := fmt.Sprintf("rm -rf %s", realLink)
		mylog.Logger.Info(rmCmd)
		_, err = RunBashCmd(rmCmd, "", nil, 1*time.Minute)
		if err != nil {
			mylog.Logger.Error(err.Error())
			return
		}
	}
	return nil
}
