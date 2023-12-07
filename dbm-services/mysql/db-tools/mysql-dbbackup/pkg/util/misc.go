package util

import (
	"bufio"
	"errors"
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

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// DiskStatus The usage information of Disk
type DiskStatus struct {
	Total uint64
	Used  uint64
	Free  uint64
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

// CalServerDataSize Calculate the data size of Mysql server
func CalServerDataSize(port int) (uint64, error) {
	datadir, err := common.GetDatadir(port)
	if err != nil {
		return 0, err
	}
	cmdStr := "du -sb " + datadir + "/.."
	res, err := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
	if err != nil {
		return 0, err
	}
	datasize := strings.Replace(string(res), "\n", "", -1)
	words := strings.Fields(datasize)
	return strconv.ParseUint(words[0], 10, 64)
}

// DiskUsage Get disk usage info
func DiskUsage(path string) (disk DiskStatus, err error) {
	switch runtime.GOOS {
	case "linux":
		fs := syscall.Statfs_t{}
		err = syscall.Statfs(path, &fs)
		if err != nil {
			return disk, err
		}
		disk.Total = fs.Blocks * uint64(fs.Bsize)
		disk.Free = fs.Bfree * uint64(fs.Bsize)
		disk.Used = disk.Total - disk.Free
	default:
		return disk, fmt.Errorf("unsupported operating system: %s", runtime.GOOS)
	}
	return disk, nil
}

// CheckDiskSpace Check whether disk free space is enough
func CheckDiskSpace(backupDir string, mysqlPort int) error {
	diskSpaceInfo, err := DiskUsage(backupDir)
	if err != nil {
		return err
	}
	backupSize, err := CalServerDataSize(mysqlPort)
	if err != nil {
		return err
	}
	if diskSpaceInfo.Free < backupSize*2 {
		err = errors.New("free space is not enough")
		return err
	}
	if float64(diskSpaceInfo.Free-backupSize*2) < 0.06*float64(diskSpaceInfo.Total) {
		err = errors.New("disk space usage may be over 94%")
		return err
	}
	return nil
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
	if strings.Contains(version, "tmysql") {
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
