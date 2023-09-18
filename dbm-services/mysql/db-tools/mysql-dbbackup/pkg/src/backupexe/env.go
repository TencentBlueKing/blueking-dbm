package backupexe

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// InnodbCommand the binary for xtrabackup
type InnodbCommand struct {
	innobackupexBin string
	xtrabackupBin   string
}

// ChooseXtrabackupTool Decide the version of xtrabackup tool
func (i *InnodbCommand) ChooseXtrabackupTool(mysqlVersion string) {
	i.innobackupexBin = "innobackupex.pl"
	i.xtrabackupBin = "xtrabackup"
	if strings.Compare(mysqlVersion, "005006000") >= 0 &&
		strings.Compare(mysqlVersion, "005007000") < 0 {
		i.innobackupexBin = "innobackupex_56.pl"
		i.xtrabackupBin = "xtrabackup_56"
	} else if strings.Compare(mysqlVersion, "005007000") >= 0 &&
		strings.Compare(mysqlVersion, "008000000") < 0 {
		i.innobackupexBin = "xtrabackup_57"
		i.xtrabackupBin = "xtrabackup_57"
	} else if strings.Compare(mysqlVersion, "008000000") >= 0 {
		i.innobackupexBin = "xtrabackup_80"
		i.xtrabackupBin = "xtrabackup_80"
	}
}

// SetEnv set env variables
func SetEnv() error {
	exepath, err := os.Executable()
	if err != nil {
		return err
	}
	exepath = filepath.Dir(exepath)
	libpath := filepath.Join(exepath, "lib/libmydumper")
	libpath2 := filepath.Join(exepath, "lib/libxtra")
	libpath3 := filepath.Join(exepath, "lib/libxtra_80")
	binpath := filepath.Join(exepath, "bin/xtrabackup")

	oldLibs := strings.Split(os.Getenv("LD_LIBRARY_PATH"), ":")
	oldLibs = append(oldLibs, libpath, libpath2, libpath3)
	err = os.Setenv("LD_LIBRARY_PATH", strings.Join(oldLibs, ":"))
	if err != nil {
		logger.Log.Error("failed to set env variable", err)
		return err
	}
	oldPaths := strings.Split(os.Getenv("PATH"), ":")
	oldPaths = append(oldPaths, binpath)
	err = os.Setenv("PATH", strings.Join(oldPaths, ":"))
	if err != nil {
		logger.Log.Error("failed to set env variable", err)
		return err
	}
	return nil
}

// GetMaxRunningTime Get MaxRunningTime from BackupTimeOut
func GetMaxRunningTime(backupTimeOut string) (int64, error) {
	deadline, err := time.Parse("15:04:05", backupTimeOut)
	if err != nil {
		logger.Log.Error("failed to parse BackupTimeOut, err: ", err)
		return 0, err
	}

	currtime := time.Now()
	duetime := time.Date(currtime.Year(), currtime.Month(), currtime.Day(),
		deadline.Hour(), deadline.Minute(), deadline.Second(), deadline.Nanosecond(), deadline.Location())
	currtimeUnix := currtime.Unix()
	duetimeUnix := duetime.Unix()
	if duetimeUnix < currtimeUnix {
		duetimeUnix += 86400
	}
	timeDiffUinx := duetimeUnix - currtimeUnix

	return timeDiffUinx, nil
}

// ParseJsonFile Parse JsonFile
func ParseJsonFile(indexPath string) (*IndexContent, error) {
	data, err := os.ReadFile(indexPath)
	if err != nil {
		logger.Log.Error(fmt.Sprintf("no such index file: %s", indexPath))
		return nil, err
	}

	var indexFileContent IndexContent
	err = json.Unmarshal(data, &indexFileContent)
	if err != nil {
		return nil, err
	}
	return &indexFileContent, nil
}
