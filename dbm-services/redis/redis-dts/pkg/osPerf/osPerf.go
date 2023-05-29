// Package osPerf 系统性能
package osPerf

import (
	"dbm-services/redis/redis-dts/tclog"
	"dbm-services/redis/redis-dts/util"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/shirou/gopsutil/v3/mem"
	"github.com/spf13/viper"
	"go.uber.org/zap"
	"golang.org/x/sys/unix"
)

// GetMyHostDisk 获取'我'所在目录的磁盘情况
func GetMyHostDisk() (myHostDisk HostDiskUsage, err error) {
	mydir, err := util.CurrentExecutePath()
	if err != nil {
		tclog.Logger.Error(err.Error())
		return myHostDisk, err
	}
	myHostDisk, err = GetLocalDirDiskUsg(mydir, tclog.Logger)
	if err != nil {
		log.Fatal(err)
	}
	return
}

// HostDiskUsage 主机磁盘使用情况(byte)
type HostDiskUsage struct {
	DirName    string `json:"MountedOn"`
	TotalSize  uint64 `json:"ToTalSize"`
	UsedSize   uint64 `json:"UsedSize"`
	AvailSize  uint64 `json:"AvailSize"`
	UsageRatio int    `json:"UsageRatio"`
}

// GetLocalDirDiskUsg 获取本地路径所在磁盘使用情况
// 参考:
// https://stackoverflow.com/questions/20108520/get-amount-of-free-disk-space-using-go
// http://evertrain.blogspot.com/2018/05/golang-disk-free.html
func GetLocalDirDiskUsg(localDir string, logger *zap.Logger) (diskUsg HostDiskUsage, err error) {
	var stat unix.Statfs_t
	if err = unix.Statfs(localDir, &stat); err != nil {
		err = fmt.Errorf("unix.Statfs fail,err:%v,localDir:%s", err, localDir)
		return
	}
	diskUsg.TotalSize = stat.Blocks * uint64(stat.Bsize)
	diskUsg.AvailSize = stat.Bavail * uint64(stat.Bsize)
	diskUsg.UsedSize = (stat.Blocks - stat.Bfree) * uint64(stat.Bsize)
	diskUsg.UsageRatio = int(diskUsg.UsedSize * 100 / diskUsg.TotalSize)
	diskUsg.DirName = localDir
	return
}

// GetHostsMemInfo 获取当前机器内存概况(byte)
func GetHostsMemInfo(logger *zap.Logger) (vMem *mem.VirtualMemoryStat, err error) {
	vMem, err = mem.VirtualMemory()
	if err != nil {
		err = fmt.Errorf("mem.VirtualMemory fail,err:%v", err)
		return
	}
	return
}

// WatchDtsSvrPerf 监听DTS server性能并发送告警
func WatchDtsSvrPerf() {
	localIP, err := util.GetLocalIP()
	if err != nil {
		tclog.Logger.Error("GetLocalIP fail", zap.Error(err))
		os.Exit(-1)
	}
	warnMsgNotifier := viper.GetString("WarnMessageNotifier")
	if warnMsgNotifier == "" {
		warnMsgNotifier = "{default_recipients}"
	}
	diskMaxUsgRatio := viper.GetInt("DtsServerDiskMaxUsgRatio")
	if diskMaxUsgRatio == 0 {
		diskMaxUsgRatio = 90
	}
	memMaxUsgRatio := viper.GetInt("DtsServerMemMaxUsgRatio")
	if memMaxUsgRatio == 0 {
		memMaxUsgRatio = 80
	}
	app := "mocpub"
	dbType := "NOSQL"
	dbCat := "DTSserver"
	warnLevel := 1
	warnType := "BACKUP"
	sendCnt := 0
	warnDetail := ""

	for {
		time.Sleep(1 * time.Minute)
		myDisk, err := GetMyHostDisk()
		if err != nil {
			continue
		}
		myMem, err := GetHostsMemInfo(tclog.Logger)
		if err != nil {
			continue
		}
		warnDetail = ""
		if myDisk.UsageRatio > diskMaxUsgRatio {
			warnDetail = fmt.Sprintf("DTS server %s disk usage:%d%% > %d%%",
				myDisk.DirName, myDisk.UsageRatio, diskMaxUsgRatio)
		} else if int(myMem.UsedPercent) > memMaxUsgRatio {
			warnDetail = fmt.Sprintf("DTS server memory usage:%.2f%% > %d%%",
				myMem.UsedPercent, memMaxUsgRatio)
		}
		if warnDetail == "" {
			continue
		}
		warnCmd := fmt.Sprintf(
			`./warn_client/warn_send.pl --app=%q --db_type=%q \\
				--db_cat=%q --ip=%q --warn_level=%d --warn_type=%s \\
				--warn_detail=%q --notifier=%q`,
			app, dbType, dbCat, localIP, warnLevel, warnType, warnDetail, warnMsgNotifier)
		util.RunLocalCmd("bash", []string{"-c", warnCmd}, "", nil, 1*time.Minute, tclog.Logger)
		sendCnt++
		if sendCnt == 3 {
			// 发送了3次后,则sleep 1 hour
			time.Sleep(30 * time.Minute)
			sendCnt = 0
		}
	}
}
