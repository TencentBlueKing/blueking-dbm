package util

import (
	"fmt"
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
