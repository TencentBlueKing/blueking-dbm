package backupexe

import (
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
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
func (i *InnodbCommand) ChooseXtrabackupTool(mysqlVersion string, isOfficial bool) error {
	if !isOfficial {
		if strings.Compare(mysqlVersion, "005005000") >= 0 &&
			strings.Compare(mysqlVersion, "005006000") < 0 {
			// tmysql 5.5
			i.innobackupexBin = "/bin/xtrabackup/innobackupex_55.pl"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_55"
		} else if strings.Compare(mysqlVersion, "005006000") >= 0 &&
			strings.Compare(mysqlVersion, "005007000") < 0 {
			// tmysql 5.6
			i.innobackupexBin = "/bin/xtrabackup/innobackupex_56.pl"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_56"
		} else if strings.Compare(mysqlVersion, "005007000") >= 0 &&
			strings.Compare(mysqlVersion, "008000000") < 0 {
			// tmysql 5.7
			i.innobackupexBin = "/bin/xtrabackup/xtrabackup_57"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_57"
		} else if strings.Compare(mysqlVersion, "008000000") >= 0 {
			// tmysql 8.0
			i.innobackupexBin = "/bin/xtrabackup/xtrabackup_80"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_80"
		} else {
			return fmt.Errorf("unrecognizable mysql version")
		}
	} else {
		if strings.Compare(mysqlVersion, "005007000") >= 0 &&
			strings.Compare(mysqlVersion, "008000000") < 0 {
			// official_mysql_5.7
			i.innobackupexBin = "/bin/xtrabackup_official/xtrabackup_57/xtrabackup"
			i.xtrabackupBin = "/bin/xtrabackup_official/xtrabackup_57/xtrabackup"
		} else if strings.Compare(mysqlVersion, "008000000") >= 0 {
			//official_mysql_8.0
			i.innobackupexBin = "/bin/xtrabackup_official/xtrabackup_80/xtrabackup"
			i.xtrabackupBin = "/bin/xtrabackup_official/xtrabackup_80/xtrabackup"
		} else {
			return fmt.Errorf("unrecognizable mysql version")
		}
	}
	return nil
}

// SetEnv set env variables
func SetEnv(backupType string, mysqlVersionStr string) error {
	exePath, err := os.Executable()
	if err != nil {
		return err
	}
	exePath = filepath.Dir(exePath)
	var libPath string
	if strings.ToLower(backupType) == "logical" {
		libPath = filepath.Join(exePath, "lib/libmydumper")
	} else if strings.ToLower(backupType) == "physical" {
		_, isOfficial := util.VersionParser(mysqlVersionStr)
		if !isOfficial {
			libPath = filepath.Join(exePath, "lib/libxtra:")
			libPath += filepath.Join(exePath, "lib/libxtra_80")
		} else {
			libPath = filepath.Join(exePath, "lib/libxtra_57_official/private:")
			libPath += filepath.Join(exePath, "lib/libxtra_57_official/plugin:")
			libPath += filepath.Join(exePath, "lib/libxtra_80_official/private:")
			libPath += filepath.Join(exePath, "lib/libxtra_80_official/plugin")
		}
	} else {
		return fmt.Errorf("setEnv: unknown backupType")
	}
	logger.Log.Info("libPath:", libPath)
	binPath := filepath.Join(exePath, "bin/xtrabackup")

	oldLibs := strings.Split(os.Getenv("LD_LIBRARY_PATH"), ":")
	oldLibs = append(oldLibs, libPath)
	err = os.Setenv("LD_LIBRARY_PATH", strings.Join(oldLibs, ":"))
	if err != nil {
		logger.Log.Error("failed to set env variable", err)
		return err
	}
	oldPaths := strings.Split(os.Getenv("PATH"), ":")
	oldPaths = append(oldPaths, binPath)
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
