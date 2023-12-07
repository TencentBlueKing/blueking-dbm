package backupexe

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// InnodbCommand the binary for xtrabackup
type InnodbCommand struct {
	innobackupexBin string
	xtrabackupBin   string
	xbcryptBin      string
}

var (
	// ExecuteHome executable home dir, like /home/mysql/dbbackup-go/
	ExecuteHome = ""
	// CmdZstd zstd command path, need call SetEnv to init
	CmdZstd = ""
	// CmdQpress qpress command path, need call SetEnv to init
	CmdQpress  = ""
	XbcryptBin = ""
)

// ChooseXtrabackupTool Decide the version of xtrabackup tool
func (i *InnodbCommand) ChooseXtrabackupTool(mysqlVersion string, isOfficial bool) error {
	if !isOfficial {
		if strings.Compare(mysqlVersion, "005005000") >= 0 &&
			strings.Compare(mysqlVersion, "005006000") < 0 {
			// tmysql 5.5
			i.innobackupexBin = "/bin/xtrabackup/innobackupex_55.pl"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_55"
			i.xbcryptBin = "/bin/xtrabackup/xbcrypt"
		} else if strings.Compare(mysqlVersion, "005006000") >= 0 &&
			strings.Compare(mysqlVersion, "005007000") < 0 {
			// tmysql 5.6
			i.innobackupexBin = "/bin/xtrabackup/innobackupex_56.pl"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_56"
			i.xbcryptBin = "/bin/xtrabackup/xbcrypt"
		} else if strings.Compare(mysqlVersion, "005007000") >= 0 &&
			strings.Compare(mysqlVersion, "008000000") < 0 {
			// tmysql 5.7
			i.innobackupexBin = "/bin/xtrabackup/xtrabackup_57"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_57"
			i.xbcryptBin = "/bin/xtrabackup/xbcrypt_57"
		} else if strings.Compare(mysqlVersion, "008000000") >= 0 {
			// tmysql 8.0
			i.innobackupexBin = "/bin/xtrabackup/xtrabackup_80"
			i.xtrabackupBin = "/bin/xtrabackup/xtrabackup_80"
			i.xbcryptBin = "/bin/xtrabackup/xbcrypt_80"
		} else {
			return fmt.Errorf("unrecognizable mysql version:%s", mysqlVersion)
		}
	} else {
		if strings.Compare(mysqlVersion, "005007000") >= 0 &&
			strings.Compare(mysqlVersion, "008000000") < 0 {
			// official_mysql_5.7
			i.innobackupexBin = "/bin/xtrabackup_official/xtrabackup_57/xtrabackup"
			i.xtrabackupBin = "/bin/xtrabackup_official/xtrabackup_57/xtrabackup"
			i.xbcryptBin = "/bin/xtrabackup_official/xtrabackup_57/xbcrypt"
		} else if strings.Compare(mysqlVersion, "008000000") >= 0 {
			//official_mysql_8.0
			i.innobackupexBin = "/bin/xtrabackup_official/xtrabackup_80/xtrabackup"
			i.xtrabackupBin = "/bin/xtrabackup_official/xtrabackup_80/xtrabackup"
			i.xbcryptBin = "/bin/xtrabackup_official/xtrabackup_80/xbcrypt"
		} else {
			return fmt.Errorf("unrecognizable mysql version:%s", mysqlVersion)
		}
	}
	return nil
}

// GetXbcryptBin get xbcrypt path for encryption, maybe for mydumper to encrypt file
// mysqlVersion format:008000018
func GetXbcryptBin(mysqlVersion string, isOfficial bool) string {
	innoCmdBin := InnodbCommand{}
	_ = innoCmdBin.ChooseXtrabackupTool(mysqlVersion, isOfficial)
	return innoCmdBin.xbcryptBin
}

// SetEnv set env variables
func SetEnv(backupType string, mysqlVersionStr string) error {
	exePath, err := os.Executable()
	if err != nil {
		return err
	}
	ExecuteHome = filepath.Dir(exePath)
	var libPath []string
	var binPath []string
	if strings.ToLower(backupType) == cst.BackupLogical {
		libPath = append(libPath, filepath.Join(ExecuteHome, "lib/libmydumper"))
	} else if strings.ToLower(backupType) == cst.BackupPhysical {
		_, isOfficial := util.VersionParser(mysqlVersionStr)
		if !isOfficial {
			libPath = append(libPath, filepath.Join(ExecuteHome, "lib/libxtra"))
			libPath = append(libPath, filepath.Join(ExecuteHome, "lib/libxtra_80"))

			binPath = append(binPath, filepath.Join(ExecuteHome, "bin/xtrabackup"))
		} else {
			libPath = append(libPath, filepath.Join(ExecuteHome, "lib/libxtra_57_official/private"))
			libPath = append(libPath, filepath.Join(ExecuteHome, "lib/libxtra_57_official/plugin"))
			libPath = append(libPath, filepath.Join(ExecuteHome, "lib/libxtra_80_official/private"))
			libPath = append(libPath, filepath.Join(ExecuteHome, "lib/libxtra_80_official/plugin"))

			binPath = append(binPath, filepath.Join(ExecuteHome, "bin/xtrabackup_official"))
		}
	} else {
		return fmt.Errorf("setEnv: unknown backupType")
	}
	// xtrabackup --decompress 需要找到 qpress 命令
	binPath = append(binPath, filepath.Join(ExecuteHome, "bin"))
	CmdZstd = filepath.Join(ExecuteHome, "bin/zstd")
	CmdQpress = filepath.Join(ExecuteHome, "bin/qpress")

	logger.Log.Info(fmt.Sprintf("export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:%s", strings.Join(libPath, ":")))
	logger.Log.Info(fmt.Sprintf("export PATH=$PATH:%s", strings.Join(binPath, ":")))

	oldLibs := strings.Split(os.Getenv("LD_LIBRARY_PATH"), ":")
	oldLibs = append(oldLibs, libPath...)
	err = os.Setenv("LD_LIBRARY_PATH", strings.Join(oldLibs, ":"))

	if err != nil {
		logger.Log.Error("failed to set env variable", err)
		return err
	}
	oldPaths := strings.Split(os.Getenv("PATH"), ":")
	oldPaths = append(oldPaths, binPath...)
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
func ParseJsonFile(indexPath string) (*dbareport.IndexContent, error) {
	data, err := os.ReadFile(indexPath)
	if err != nil {
		logger.Log.Error(fmt.Sprintf("no such index file: %s", indexPath))
		return nil, err
	}

	var indexFileContent dbareport.IndexContent
	err = json.Unmarshal(data, &indexFileContent)
	if err != nil {
		return nil, err
	}
	return &indexFileContent, nil
}
