package logparserjob

import (
	"dbm-services/mongodb/db-tools/dbmon/pkg/psutil"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
	"time"
)

// getLastRotate 获取文件最后一次rotate的时间. 如果文件不存在，返回0
// .last_rotate 文件用于记录上次rotate的时间
func getLastRotate(mongoFilePath string) int64 {
	dir := filepath.Dir(mongoFilePath)
	touchPath := filepath.Join(dir, ".last_rotate")
	fileInfo, err := os.Stat(touchPath)
	if err != nil {
		if os.IsNotExist(err) {
			// 如果rotate文件不存在，总是rotate一次
			touchRotateFile(touchPath)
			return -1 // 返回-1表示总是rotate一次
		} else {
			touchRotateFile(touchPath)
			return 0
		}
	}
	return fileInfo.ModTime().Unix()
}

// touchRotateFile 更新文件的最后一次rotate时间
func touchRotateFile(mongoFilePath string) error {
	dir := filepath.Dir(mongoFilePath)
	touchPath := filepath.Join(dir, ".last_rotate")
	return os.WriteFile(touchPath, []byte("rotate"), 0666)
}

// rotateMongoLog rotates the mongo log file.
// If the file size exceeds maxSize, it will be rotated.
// or if the file has not been rotated for more than a day, it will be rotated.
// 如果不存在rotate文件，或者rotate文件更新超过一天，总是rotate一次。避免读到过多的旧数据.
func (w *Worker) rotateMongoLog(mongoLogFilePath string, maxSize int64, minTime int64) error {
	// 如果mongo.log文件不存在，不rotate
	fileInfo, err := os.Stat(mongoLogFilePath)
	if err != nil {
		return err
	}

	firstInitCond := false
	lastRotateTime := getLastRotate(mongoLogFilePath)

	// 如果是第一次初始化，总是rotate一次，避免读到过多的旧数据
	if lastRotateTime == -1 {
		firstInitCond = true
	}

	timeDiff := time.Now().Unix() - lastRotateTime
	// 如果和上次rotate的时间相差超过一天，总是rotate一次，避免读到过多的旧数据
	timeCond := timeDiff > secondsDay
	if timeCond {
		// 如果是时间的原因分割，那要在每天的4时分割，这样分出来的文件会好看一点.
		timeCond = timeCond && time.Now().Hour() == 3
	}

	// 如果文件大小超过maxSize，rotate
	sizeCond := timeDiff < minTime && fileInfo.Size() > maxSize

	w.Logger.Info(fmt.Sprintf("debug rotateMongoLog: %s, size: %d, "+
		"lastRotateTime: %d firstInitCond:%v timeCond:%v sizeCond %v",
		mongoLogFilePath, fileInfo.Size(), lastRotateTime, firstInitCond, timeCond, sizeCond),
	)

	if !sizeCond && !timeCond && !firstInitCond {
		return nil
	}
	pid, err := psutil.GetPidByPort(w.Server.Port, w.Logger)
	if err != nil {
		w.Logger.Error(fmt.Sprintf("GetPidByPort failed. port %d: err %v", w.Server.Port, err))
		return err
	}

	err = syscall.Kill(pid, syscall.SIGUSR1)
	if err == nil {
		touchRotateFile(mongoLogFilePath)
		w.Logger.Info(fmt.Sprintf("send SIGUSR1 to pid %d success", pid))
	} else {
		w.Logger.Info(fmt.Sprintf("send SIGUSR1 to pid %d failed, err %v", pid, err))
	}
	return err
}
