package util

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// DiskStatus The usage information of Disk
type DiskStatus struct {
	Total      uint64 // total device block size, include reserved by os filesystem
	Free       uint64 // free size include reserved by os filesystem
	Used       uint64 // actually used
	Avail      uint64 // available size
	TotalAvail uint64 // available total size (total - reserved)
	Reserved   uint64 // reserved by os filesystem
}

// FileExist check whether the file exist
func FileExist(path string) (bool, error) {
	_, err := os.Stat(path)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, err
}

// FileExistReturnSize check whether the file exist
func FileExistReturnSize(path string) (bool, int64, error) {
	fd, err := os.Stat(path)
	if err == nil {
		return true, fd.Size(), nil
	}
	if os.IsNotExist(err) {
		return false, 0, nil
	}
	return false, 0, err
}

// CopyFile copy src file to des file
func CopyFile(desPath string, srcPath string) error {
	srcFileStat, err := os.Stat(srcPath)
	if err != nil {
		return err
	}
	if !srcFileStat.Mode().IsRegular() {
		return fmt.Errorf("%s is not a regular fiile", srcPath)
	}
	srcFile, err := os.Open(srcPath)
	if err != nil {
		return err
	}
	defer func() {
		_ = srcFile.Close()
	}()

	desFile, err := os.Create(desPath)
	if err != nil {
		return err
	}
	defer func() {
		_ = desFile.Close()
	}()

	_, err = io.Copy(desFile, srcFile)
	return err
}

// CheckIntegrity Check the integrity of backup file
func CheckIntegrity(publicConfig *config.Public) error {
	if strings.ToLower(publicConfig.BackupType) == cst.BackupLogical {
		backupPath := publicConfig.BackupDir + "/" + publicConfig.TargetName()

		fileExist0, err := FileExist(backupPath)
		if !fileExist0 {
			logger.Log.Error(fmt.Sprintf("backup file path: %s dosen't exist, error: %v", backupPath, err))
			return err
		}

		fileExist1, err1 := FileExist(backupPath + "/metadata")
		if !fileExist1 {
			logger.Log.Error(fmt.Sprintf("backup file path: %s dosen't exist, error: %v", backupPath, err1))
			return err1
		}
	}
	return nil
}

// CalServerDataSize Calculate the data size bytes of Mysql server
func CalServerDataSize(port int) (uint64, error) {
	datadir, err := common.GetDataHomeDir(port)
	if err != nil {
		return 0, err
	}
	cmdStr := "du -sb " + datadir
	res, err := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
	if err != nil {
		return 0, errors.WithMessage(err, string(res))
	}
	datasize := strings.Replace(string(res), "\n", "", -1)
	words := strings.Fields(datasize)
	return strconv.ParseUint(words[0], 10, 64)
}

// DiskUsage Get disk usage info
func DiskUsage(path string) (disk DiskStatus, err error) {
	switch runtime.GOOS {
	case "linux":
		if realPath, _ := os.Readlink(path); realPath != "" {
			path = realPath
		}
		fs := syscall.Statfs_t{}
		err = syscall.Statfs(path, &fs)
		if err != nil {
			return disk, err
		}
		disk.Total = fs.Blocks * uint64(fs.Bsize)
		disk.Free = fs.Bfree * uint64(fs.Bsize)   // free include reserved (free = avail + reserved)
		disk.Avail = fs.Bavail * uint64(fs.Bsize) // avail is little than free usually
		disk.Used = disk.Total - disk.Free
		disk.Reserved = disk.Free - disk.Avail
		disk.TotalAvail = disk.Avail + disk.Used // equal disk.Total - disk.Reserved
	default:
		return disk, fmt.Errorf("unsupported operating system: %s", runtime.GOOS)
	}
	return disk, nil
}

// CheckDiskSpace Check whether disk free space is enough
// err != nil
//  1. 如果返回的值 <0，则表示空间不足，且还需要对应的空间大小
//  2. 其他未知错误
//
// err == nil
//  1. 如果返回值 >0，则表示空间足够，且还剩余的空间大小
func CheckDiskSpace(backupDir string, mysqlPort int, backupSize uint64) (sizeLeft int64, err error) {
	diskSpaceInfo, err := DiskUsage(backupDir)
	if err != nil {
		return 0, err
	}
	logger.Log.Infof("backupDir %s disk info: %+v", backupDir, diskSpaceInfo)
	expectSize := backupSize*1 + 5*1024*1024*1024 // 预计备份需要多少实际空间
	expectSizeLeft := float64(diskSpaceInfo.Avail) - float64(expectSize)
	if expectSizeLeft < 0 {
		err = errors.New("free space is not enough")
		return int64(expectSizeLeft), err
	}
	sizeLeft = int64(expectSizeLeft - 0.06*float64(diskSpaceInfo.TotalAvail))
	if sizeLeft < 0 { // 为负，说明expectSize用掉后，空间可能会超过 94%
		err = errors.New("disk space usage may be over 94%")
		return sizeLeft, err
	}
	return sizeLeft, nil
}

// ExeCommand execute shell command
func ExeCommand(cmdStr string) error {
	res, exeErr := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
	logger.Log.Info("execute ", cmdStr, " ,result :", string(res))
	if exeErr != nil {
		logger.Log.Error("Failed to execute command, error: ", exeErr)
		return exeErr
	}
	return nil
}

// GetMyCnfKeyValue get the key-value from my.cnf
func GetMyCnfKeyValue(myCnfPath string, key string) (value string, err error) {
	myCnfFile, err := os.Open(myCnfPath)
	if err != nil {
		return value, err
	}
	defer func() {
		_ = myCnfFile.Close()
	}()

	buf := bufio.NewScanner(myCnfFile)
	for buf.Scan() {
		line := buf.Text()
		// match key
		if strings.Contains(line, key) {
			// todo
			return value, nil
		}
		// get value
	}
	return value, err
}

// StringSliceToInterfaceSlice 把字符串数组转换为interface{}数组
func StringSliceToInterfaceSlice(ids []string) []interface{} {
	var result []interface{}
	if len(ids) == 1 {
		result = append(result, ids[0])
	} else {
		for i := 0; i < len(ids); i++ {
			result = append(result, ids[i])
		}
	}
	return result
}

// VersionParser parse mysql version.
// example:
// tmysql-version: 5.7.20-tmysql-3.4.2-log -> return 005007020, false
// official-version: 5.7.42-log -> return 005007042, true
func VersionParser(version string) (parse string, isOfficial bool) {
	parse = "000000"
	reg := regexp.MustCompile(`^\s*(\d+)\.(\d+)\.(\d+)`)
	temp := reg.FindStringSubmatch(version)
	if len(temp) > 0 {
		temp = append(temp[:0], temp[1:]...)
		newTemp := StringSliceToInterfaceSlice(temp)
		parse = fmt.Sprintf("%03s%03s%03s", newTemp...)
	}
	if strings.Contains(version, "tmysql") || strings.Contains(version, "txsql") {
		isOfficial = false
	} else {
		isOfficial = true
	}
	return parse, isOfficial
}

// FindBackupConfigFiles TODO
func FindBackupConfigFiles(dir string) ([]string, error) {
	globFilename := "dbbackup.*.ini"
	if dir != "" {
		globFilename = filepath.Join(dir, globFilename)
	}
	cnfFiles, err := filepath.Glob(globFilename)
	if err != nil {
		return nil, err
	}
	var cnfFilesNew []string
	reFilename := regexp.MustCompile(`dbbackup\.(\d)+\.ini`)
	for _, f := range cnfFiles {
		if reFilename.MatchString(f) {
			cnfFilesNew = append(cnfFilesNew, f)
		}
	}
	return cnfFilesNew, nil
}

// GetMaxRunningTime Get MaxRunningTime from BackupTimeOut
func GetMaxRunningTime(backupTimeOut string) (int64, error) {
	deadline, err := time.ParseInLocation("15:04:05", backupTimeOut, time.Local)
	if err != nil {
		logger.Log.Error("failed to parse BackupTimeOut, err: ", err)
		return 0, err
	}

	nowTime := time.Now().Local()
	duetime := time.Date(nowTime.Year(), nowTime.Month(), nowTime.Day(),
		deadline.Hour(), deadline.Minute(), deadline.Second(), deadline.Nanosecond(), deadline.Location())
	currtimeUnix := nowTime.Unix()
	duetimeUnix := duetime.Unix()
	if duetimeUnix < currtimeUnix {
		duetimeUnix += 86400
	}
	timeDiffUinx := duetimeUnix - currtimeUnix

	return timeDiffUinx, nil
}
