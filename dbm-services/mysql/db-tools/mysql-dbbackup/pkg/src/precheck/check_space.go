package precheck

import (
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// DeleteOldBackup Delete expired backup file
func DeleteOldBackup(cnf *config.Public, expireDays int) error {
	expireTime := time.Now().AddDate(0, 0, -1*expireDays)
	logger.Log.Infof("try to remove old backup files before %s", expireTime)
	dir, err := ioutil.ReadDir(cnf.BackupDir)
	if err != nil {
		logger.Log.Error("failed to read backupdir, err :", err)
		return err
	}

	// old backup file targetName has hostname
	output, err := exec.Command("hostname").CombinedOutput()
	if err != nil {
		logger.Log.Warn("failed to get hostname")
		return err
	}
	hostName := strings.Replace(string(output), "\n", "", -1)

	for _, fi := range dir {
		fileMatchOld := fmt.Sprintf("%s_%s", hostName, cnf.MysqlHost)
		filePrefix := fmt.Sprintf("%d_%d_%s", cnf.BkBizId, cnf.ClusterId, cnf.MysqlHost)
		if fi.ModTime().Compare(expireTime) <= 0 {
			if strings.HasPrefix(fi.Name(), filePrefix) || strings.Contains(fi.Name(), fileMatchOld) {
				fileName := filepath.Join(cnf.BackupDir, fi.Name())
				if fi.Size() > 4*1024*1024*1024 {
					logger.Log.Infof("remove old backup file %s limit %dMB/s ", fileName, 500)
					if err2 := cmutil.TruncateFile(fileName, 500); err2 != nil {
						// 尽可能清理，记录最后一个错误
						err = err2
						continue
					}
				} else {
					logger.Log.Info("remove old backup file ", fileName)
					if err2 := os.RemoveAll(fileName); err2 != nil {
						err = err2
						continue
					}
				}
			}
		}
	}
	return err
}

// EnableBackup 如果空间不足，则会强制删除所有备份文件
func EnableBackup(cnf *config.Public) error {
	if _, err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort); err == nil {
		return nil
	}
	err := DeleteOldBackup(cnf, 0)
	if err != nil {
		// 文件清理错误，只当做 warning
		logger.Log.Warn("failed to delete old backup again, err:", err)
	}
	sizeLeft, err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort)
	if err == nil {
		return nil
	} else {
		logger.Log.Warn("clean backup: %s", err.Error())
	}
	if sizeLeft < 0 {
		cleanBinlogCmd := []string{"rotatebinlog", "clean-space", "--max-disk-used-pct", "20"}
		//"--size-to-free", cast.ToString(math.Abs(float64(sizeLeft)))
		logger.Log.Info("clean binlog: %s", strings.Join(cleanBinlogCmd, " "))
		// 如果备份全部清理完成，预测空间还不够备份，则请求清理 binlog
		_, strErr, err := cmutil.ExecCommand(false, cst.MysqlRotateBinlogInstallPath,
			cleanBinlogCmd[0], cleanBinlogCmd[1:]...)
		if err != nil {
			logger.Log.Warn("rotatebinlog clean-space failed: %s, %s", err.Error(), strErr)
		}
	}
	return nil
}
