/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package precheck

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// DeleteOldBackup Delete expired backup file
func DeleteOldBackup(cnf *config.Public, expireDays int) error {
	expireTime := time.Now().AddDate(0, 0, -1*expireDays)
	logger.Log.Infof("try to remove old backup files before '%s'", expireTime)
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
		fileMatch := fmt.Sprintf("_%d_%s", cnf.ClusterId, cnf.MysqlHost) // cnf.BkBizId 转业务了历史的也要删除
		if fi.ModTime().Compare(expireTime) <= 0 {
			if strings.Contains(fi.Name(), fileMatch) || strings.Contains(fi.Name(), fileMatchOld) {
				fileName := filepath.Join(cnf.BackupDir, fi.Name())
				if fi.Size() > 4*1024*1024*1024 {
					// remove 速度适度放大一点
					removeLimit := cnf.IOLimitMBPerSec
					logger.Log.Infof("remove old backup file %s limit %dMB/s ", fileName, removeLimit)
					if err2 := cmutil.TruncateFile(fileName, removeLimit); err2 != nil {
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

// CheckAndCleanDiskSpace 如果空间不足，则会强制删除所有备份文件
func CheckAndCleanDiskSpace(cnf *config.Public, dbh *sql.DB) error {
	dataDirSize, err := util.CalServerDataSize(cnf.MysqlPort)
	if err != nil {
		return err
	}
	// 第一次检查，空间满足直接通过
	if sizeLeft, err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort, dataDirSize); err == nil {
		logger.Log.Infof("disk space meets ok1, sizeLeft=%d, dataDirSize=%d", sizeLeft, dataDirSize)
		return nil
	}
	// 删除旧备份后，第二次检查
	if err = DeleteOldBackup(cnf, 0); err != nil {
		// 文件清理错误，只当做 warning
		logger.Log.Warn("failed to delete old backup again, err:", err)
	}
	if cnf.NoCheckDiskSpace {
		logger.Log.Warnf("not check disk space for port %d", cnf.MysqlPort)
		return nil
	}

	sizeLeft, err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort, dataDirSize)
	if err == nil {
		logger.Log.Infof("disk space meets ok2, sizeLeft=%d, dataDirSize=%d", sizeLeft, dataDirSize)
		return nil
	} else {
		logger.Log.Warnf("clean all backups still does not meet space needed: %s", err.Error())
	}
	if sizeLeft <= 0 {
		// 删除 binlog，第三次检查
		cleanBinlogCmd := []string{"./rotatebinlog", "clean-space", "--max-disk-used-pct", "20"}
		//"--size-to-free", cast.ToString(math.Abs(float64(sizeLeft)))
		logger.Log.Infof("to backup %d, clean binlog: %s", cnf.MysqlPort, strings.Join(cleanBinlogCmd, " "))
		// 如果备份全部清理完成，预测空间还不够备份，则请求清理 binlog
		_, strErr, err := cmutil.ExecCommand(false, cst.MysqlRotateBinlogInstallPath,
			cleanBinlogCmd[0], cleanBinlogCmd[1:]...)
		if err != nil {
			logger.Log.Warnf("to backup %d, rotatebinlog clean-space failed: %s, %s",
				cnf.MysqlPort, err.Error(), strErr)
		}

		// 如果空间还不满足，尝试找上一个全备的大小，因为实际可能并不需要这么 dataDir 空间大小
		lastBackupSize, err := GetLastBackupSize(cnf, dbh)
		if err != nil {
			logger.Log.Warn("failed to GetLastBackupSize, err:", err)
		}
		if lastBackupSize > 0 {
			sizeLeft, err = util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort, lastBackupSize)
			logger.Log.Infof("evaluate using last backup size=%d, sizeLeft=%d, BackupDir=%s err=%v",
				lastBackupSize, sizeLeft, cnf.BackupDir, err)
		} else {
			sizeLeft, err = util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort, dataDirSize)
			logger.Log.Infof("evaluate using datadir size=%d, sizeLeft=%d, BackupDir=%s err=%v",
				dataDirSize, sizeLeft, cnf.BackupDir, err)
		}
		return err
	} else {
		logger.Log.Infof("disk space meets ok3, sizeLeft=%d, dataDirSize=%d", sizeLeft, dataDirSize)
	}
	return nil
}

func GetLastBackupSize(cnf *config.Public, db *sql.DB) (uint64, error) {
	whereStr := fmt.Sprintf("backup_type = %s and  cluster_address = %s and backup_port = %d "+
		" and is_full_backup = 1 and backup_begin_time > DATE_SUB(now(), INTERVAL 10 DAY) and backup_meta_file != ''",
		mysqlcomm.UnsafeEqual(cnf.BackupType, "'"),
		mysqlcomm.UnsafeEqual(cnf.ClusterAddress, "'"),
		cnf.MysqlPort)

	sqlBuilder := sq.Select("backup_id", "backup_begin_time", "extra_fields").
		From(dbareport.ModelBackupReport{}.TableName()).
		Where(whereStr).OrderBy("backup_begin_time desc").Limit(1)

	sqlStr, _, err := sqlBuilder.ToSql()
	if err != nil {
		return 0, err
	}
	logger.Log.Infof("GetLastBackupSize sql: %s", sqlStr)
	res := db.QueryRow(sqlStr)
	var backupId, backupTime, extraFieldsStr string
	if err = res.Scan(&backupId, &backupTime, &extraFieldsStr); err != nil {
		return 0, errors.WithMessagef(err, "query the last full backup size for %d", cnf.MysqlPort)
	}
	extraFields := dbareport.ExtraFields{}
	if err = json.Unmarshal([]byte(extraFieldsStr), &extraFields); err != nil {
		return 0, err
	}
	logger.Log.Infof("GetLastBackupSize for backup_id=%s, backup_type=%s, backup_time=%s extra_fields=%+v",
		backupId, cnf.BackupType, backupTime, extraFields)
	return extraFields.TotalFilesize, nil
}
