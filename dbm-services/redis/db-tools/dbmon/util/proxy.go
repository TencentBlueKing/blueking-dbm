package util

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
)

// GetTwemproxyLastLogFile TODO
func GetTwemproxyLastLogFile(port int) (logFile string, err error) {
	var files []string
	var ret string
	grepCmd := fmt.Sprintf(
		`ps aux|grep nutcracker|grep -v grep|grep -P --only-match "\\-o\s+.*/twemproxy.%d.log"|awk '{print $2}' || { true; }`,
		port)
	ret, err = RunBashCmd(grepCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	ret = strings.TrimSpace(ret)
	if ret == "" {
		// 如果twemproxy进程不存在，则从日志目录中获取
		ret = fmt.Sprintf("%s/twemproxy*/%d/log/twemproxy.%d.log", consts.GetRedisDataDir(), port, port)
	}
	files, err = filepath.Glob(ret + "*")
	if err != nil {
		err = fmt.Errorf("filepath.Glob(%s*) failed,err:%v", ret, err)
		mylog.Logger.Error(err.Error())
		return
	}
	maxMtime := time.Time{}
	var fs os.FileInfo
	for _, file := range files {
		// 获取 mtime 为最新的文件
		if file == "" {
			continue
		}
		fs, err = os.Stat(file)
		if err != nil {
			continue
		}
		if fs.ModTime().After(maxMtime) {
			maxMtime = fs.ModTime()
			logFile = file
		}
	}
	return
}

// GetPredixyLastLogFile TODO
func GetPredixyLastLogFile(port int) (logFile string, err error) {
	grepCmd := fmt.Sprintf(`grep -Pi "^Log\s+" %s/predixy/%d/predixy.conf|awk '{print $NF}'|| { true; }`,
		consts.GetRedisDataDir(), port)
	logFile, err = RunBashCmd(grepCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	logFile = strings.TrimSpace(logFile)
	if logFile == "" {
		logFile = fmt.Sprintf("%s/predixy/%d/logs/log", consts.GetRedisDataDir(), port)
	}
	return
}
