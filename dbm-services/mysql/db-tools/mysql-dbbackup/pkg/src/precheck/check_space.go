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
					if err = cmutil.TruncateFile(fileName, 500); err != nil {
						return err
					}
				} else {
					logger.Log.Info("remove old backup file ", fileName)
					if err = os.RemoveAll(fileName); err != nil {
						return err
					}
				}
			}
		}
	}
	return nil
}

// EnableBackup Check whether backup is allowed
func EnableBackup(cnf *config.Public) error {
	if err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort); err == nil {
		return nil
	}
	err := DeleteOldBackup(cnf, 0)
	if err != nil {
		return err
	}
	return util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort)
}
