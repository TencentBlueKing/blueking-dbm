// Package cleanOldTasksDir TODO
package cleanOldTasksDir

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/redis-dts/tclog"
	"dbm-services/redis/redis-dts/util"
)

var globCleanOldTasksDir *Job
var cleanOnce sync.Once

// Job TODO
type Job struct {
}

// GetGlobCleanOldTasksDir get	globCleanOldTasksDir
func GetGlobCleanOldTasksDir() *Job {
	cleanOnce.Do(func() {
		globCleanOldTasksDir = &Job{}
	})
	return globCleanOldTasksDir
}

// Run 运行
func (job *Job) Run() {
	mydir, err := util.CurrentExecutePath()
	if err != nil {
		tclog.Logger.Error(err.Error())
		return
	}
	taskDir := filepath.Join(mydir, "tasks")

	// 180天前的时间
	threshold := time.Now().Local().AddDate(0, 0, -180)

	// 读取目录内容
	entries, err := os.ReadDir(taskDir)
	if err != nil {
		tclog.Logger.Error(fmt.Sprintf("os.ReadDir() %s return err:%v\n", taskDir, err))
		return
	}
	for _, entry := range entries {
		if entry.IsDir() {
			// 获取目录完整路径
			dirPath := filepath.Join(taskDir, entry.Name())

			// 获取目录的文件信息
			dirInfo, err := os.Stat(dirPath)
			if err != nil {
				tclog.Logger.Error(fmt.Sprintf("os.Stat() %s return err:%v\n", dirPath, err))
				continue
			}
			// 判断是否是60天前的目录
			if dirInfo.ModTime().Before(threshold) {
				if job.isDtsTasksRunning(entry.Name()) {
					tclog.Logger.Info(fmt.Sprintf("目录:%s 180天前创建的,但是依然有tasks还在运行,跳过删除", entry.Name()))
					continue
				}
				// 删除目录
				rmCmd := fmt.Sprintf("cd %s && rm -rf %s", taskDir, entry.Name())
				tclog.Logger.Info(fmt.Sprintf("删除180天前创建的目录:%s", rmCmd))
				util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 1*time.Hour, tclog.Logger)
			}
		}
	}
}

func (job *Job) isDtsTasksRunning(taskSubDirName string) bool {
	psCmd := fmt.Sprintf("ps -ef | grep %s | grep -v grep | wc -l", taskSubDirName)
	ret, err := util.RunLocalCmd("bash", []string{"-c", psCmd}, "", nil, 1*time.Hour, tclog.Logger)
	if err != nil {
		return false
	}
	ret = strings.TrimSpace(ret)
	if ret == "0" {
		return false
	}
	return true
}
