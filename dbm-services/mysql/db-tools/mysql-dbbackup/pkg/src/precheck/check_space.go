package precheck

import (
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// DeleteOldBackup Delete expired backup file
func DeleteOldBackup(cnf *parsecnf.CnfShared, expireDays int) error {
	currTime := time.Now().Unix()
	diffTime := expireDays * 24 * 3600

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
		fileTime := fi.ModTime().Unix()
		filePrefixOld := strings.Join([]string{cnf.BkBizId, hostName, cnf.MysqlHost}, "_")
		filePrefix := strings.Join([]string{cnf.BkBizId, cnf.ClusterId, cnf.MysqlHost}, "_")
		if strings.HasPrefix(fi.Name(), filePrefix) || strings.HasPrefix(fi.Name(), filePrefixOld) {
			if (currTime - fileTime) > int64(diffTime) {
				if err = os.RemoveAll(filepath.Join(cnf.BackupDir, fi.Name())); err != nil {
					logger.Log.Error("failed to remove file, err :", err)
					return err
				}
			}
		}
	}
	return nil
}

// EnableBackup Check whether backup is allowed
func EnableBackup(cnf *parsecnf.CnfShared) error {
	if err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort); err == nil {
		return nil
	}
	err := DeleteOldBackup(cnf, 0)
	if err != nil {
		return err
	}
	return util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort)
}
