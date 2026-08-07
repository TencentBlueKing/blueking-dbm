/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package backupexe

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/huandu/go-sqlbuilder"
	"github.com/jmoiron/sqlx"
	errs "github.com/pkg/errors"
	"github.com/sirupsen/logrus"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// DeleteOldBackup Delete expired backup file
// expireDays =0  时表示删除所有备份，但依然会保留其它端口的 12h 内的备份
// 返回删除的总字节数和错误
func DeleteOldBackup(cnf *config.Public, expireDays int) (int64, error) {
	var freedBytes int64
	defer func() {
		// 只要调用 DeleteOldBackup ，则清理一下本地备份报告
		if db, err := mysqlconn.InitConnx(cnf, context.Background()); err == nil {
			cleanLocalBackupReport(cnf.MysqlHost, cnf.MysqlPort, db, logger.Log)
			db.Close()
		}
	}()

	expireTime := time.Now().AddDate(0, 0, -1*expireDays)
	logger.Log.Infof("try to remove old backup files before '%s'", expireTime)
	dir, err := ioutil.ReadDir(cnf.BackupDir)
	if err != nil {
		logger.Log.Error("failed to read backupdir, err :", err)
		return 0, err
	}
	hostEscaped := regexp.QuoteMeta(cnf.MysqlHost)
	matchHost := fmt.Sprintf("_%s_", hostEscaped)
	matchInstance := fmt.Sprintf("%s_%d", hostEscaped, cnf.MysqlPort)
	reHost := regexp.MustCompile(matchHost)
	reInstance := regexp.MustCompile(matchInstance)
	// backup file format: 123_1234567_1.2.3.4_3306_20260324092001_XX
	reBakFile := regexp.MustCompile(fmt.Sprintf(`\d+_\d+_%s_`, hostEscaped))
	indexFiles := map[string]time.Time{}
	bakFiles := map[string]int64{}
	for _, fi := range dir {
		if reBakFile.MatchString(fi.Name()) {
			bakFiles[fi.Name()] = fi.Size()
			if strings.HasSuffix(fi.Name(), cst.SuffixIndex) {
				indexFiles[fi.Name()] = fi.ModTime()
			}
		}
	}
	indexFilesKeep := []string{}
	for indexFile, modTime := range indexFiles {
		canRemove := false
		if reInstance.MatchString(indexFile) && expireTime.Compare(modTime) > 0 {
			// 本实例的备份，指定时间(可能是 now)之前的允许全部删掉
			canRemove = true
		} else if reHost.MatchString(indexFile) && !reInstance.MatchString(indexFile) {
			// 其它实例的备份，如果要全部清理，也要限制只能删除 12h 之前的
			if expireDays > 0 && expireTime.Compare(modTime) > 0 {
				canRemove = true
			} else if expireDays <= 0 && time.Now().Sub(modTime).Hours() > 12 {
				canRemove = true
			}
		}
		if canRemove {
			for bakFileName, bakFileSize := range bakFiles {
				indexFilePrefix := strings.TrimSuffix(indexFile, cst.SuffixIndex)
				if strings.HasPrefix(bakFileName, indexFilePrefix) {
					removed, rmErr := removeFile(cnf, bakFileName, bakFileSize)
					err = errors.Join(err, rmErr)
					freedBytes += removed
					bakFiles[bakFileName] = -1 // mark element deleted
				}
			}
		} else {
			indexFilesKeep = append(indexFilesKeep, indexFile)
		}
	}

	// 还有一类是脏数据，已经没有 .index 了，但备份文件还在，也需要清理
	for bakFileName, bakFileSize := range bakFiles {
		if bakFileSize == -1 { // deleted already
			continue
		}
		belongsToKeep := false
		for _, indexFile := range indexFilesKeep {
			indexFilePrefix := strings.TrimSuffix(indexFile, cst.SuffixIndex)
			if strings.HasPrefix(bakFileName, indexFilePrefix) {
				belongsToKeep = true
				break
			}
		}
		if !belongsToKeep {
			removed, rmErr := removeFile(cnf, bakFileName, bakFileSize)
			err = errors.Join(err, rmErr)
			freedBytes += removed
		}
	}
	return freedBytes, err
}

// removeFile 删除文件并返回删除的字节数
func removeFile(cnf *config.Public, fileName string, fileSize int64) (int64, error) {
	if fileName == "" || fileSize == -1 {
		return 0, nil
	} else if fileName[0] != '/' {
		fileName = filepath.Join(cnf.BackupDir, fileName)
	}
	removedSize := fileSize
	if fileSize > 4*1024*1024*1024 {
		// remove 速度适度放大一点
		removeLimit := cnf.IOLimitMBPerSec + 300
		logger.Log.Infof("remove old backup file %s limit %dMB/s ", fileName, removeLimit)
		if err := cmutil.TruncateFile(fileName, removeLimit); err != nil {
			logger.Log.Warnf("remove %s got error:%s", fileName, err.Error())
			// 尽可能清理，记录最后一个错误
			return 0, err
		}
	} else {
		logger.Log.Info("remove old backup file ", fileName)
		if err := os.RemoveAll(fileName); err != nil {
			logger.Log.Warnf("remove %s got error:%s", fileName, err.Error())
			return 0, err
		}
	}
	return removedSize, nil
}

// cleanLocalBackupReport 维持 local_backup_report 表里面的记录状态
// 当本地文件 index 文件不存在时，将备份状态置为 local_removed
func cleanLocalBackupReport(host string, port int, db *sqlx.DB, l *logrus.Logger) (err error) {
	ctx := context.Background()
	db = db.Unsafe()
	session, _ := db.Connx(ctx)
	defer session.Close()

	tableName := dbareport.ModelLocalBackupReport{}.TableName()
	var metaFiles []*dbareport.ModelLocalBackupReport
	builder := sqlbuilder.Select("backup_id", "mysql_role", "shard_value", "backup_host", "backup_port",
		"backup_status", "cluster_id", "cluster_address", "data_schema_grant", "backup_method", "backup_meta_file").
		From(tableName)
	builder.Where(
		//builder.Equal("backup_host", host),
		builder.Equal("backup_port", port),
		builder.NotEqual("backup_status", cst.LocalRemoved),
	)
	sqlStr, sqlArgs := builder.BuildWithFlavor(sqlbuilder.MySQL)
	sqlFull, err := sqlbuilder.MySQL.Interpolate(sqlStr, sqlArgs)
	if err != nil {
		return err
	}
	if err = session.SelectContext(ctx, &metaFiles, sqlFull); err != nil {
		l.Error("failed to query local backup report, err:", err)
		return err
	}
	if _, err = session.ExecContext(ctx, "set sql_log_bin=0;"); err != nil {
		l.Error("failed to set sql_log_bin=0, err:", errs.WithMessage(err, "update local_backup_report"))
		// 必须关闭 binlog，不然可能会出现主从复制报错
		return err
	}
	for _, backupMeta := range metaFiles {
		if cmutil.FileExists(backupMeta.BackupMetaFile) {
			continue
		}
		//backupMeta.BackupStatus = cst.LocalRemoved
		updateBuilder := sqlbuilder.Update(tableName)
		updateBuilder.Set(updateBuilder.Assign("backup_status", cst.LocalRemoved)).
			Where(
				updateBuilder.Equal("backup_id", backupMeta.BackupId),
				//updateBuilder.Equal("backup_host", backupMeta.BackupHost),
				updateBuilder.Equal("backup_port", backupMeta.BackupPort),
			)
		sqlStr, sqlArgs := updateBuilder.Build()
		sqlFull, err = sqlbuilder.MySQL.Interpolate(sqlStr, sqlArgs)
		if err != nil {
			l.Error("failed to update backup report, err:", err)
			continue
		}
		if _, err = session.ExecContext(ctx, sqlFull); err != nil {
			l.Error("failed to update backup report, err:", err)
			continue
		}
	}
	return nil
}

// CheckAndCleanDiskSpace 如果空间不足，则会强制删除所有备份文件
func CheckAndCleanDiskSpace(cnf *config.Public, dataDirSizeBytes uint64, dbh *sql.DB) (err error) {
	// 第一次检查，空间满足直接通过
	if sizeLeft, err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort, dataDirSizeBytes); err == nil {
		logger.Log.Infof("disk space meets ok1, sizeLeft=%d, dataDirSize=%d", sizeLeft, dataDirSizeBytes)
		return nil
	}
	// 删除旧备份后，第二次检查
	if _, err = DeleteOldBackup(cnf, 0); err != nil {
		// 文件清理错误，只当做 warning
		logger.Log.Warn("failed to delete old backup again, err:", err)
	}
	if cnf.NoCheckDiskSpace {
		logger.Log.Warnf("not check disk space for port %d", cnf.MysqlPort)
		return nil
	}

	sizeLeft, err := util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort, dataDirSizeBytes)
	if err == nil {
		logger.Log.Infof("disk space meets ok2, sizeLeft=%d, dataDirSize=%d", sizeLeft, dataDirSizeBytes)
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
			sizeLeft, err = util.CheckDiskSpace(cnf.BackupDir, cnf.MysqlPort, dataDirSizeBytes)
			logger.Log.Infof("evaluate using datadir size=%d, sizeLeft=%d, BackupDir=%s err=%v",
				dataDirSizeBytes, sizeLeft, cnf.BackupDir, err)
		}
		return err
	} else {
		logger.Log.Infof("disk space meets ok3, sizeLeft=%d, dataDirSize=%d", sizeLeft, dataDirSizeBytes)
	}
	return nil
}

// GetLastBackupSize 获取上一个全备的大小
func GetLastBackupSize(cnf *config.Public, db *sql.DB) (uint64, error) {
	whereStr := fmt.Sprintf("backup_type = %s and  cluster_address = %s and backup_port = %d "+
		" and is_full_backup = 1 and backup_begin_time > DATE_SUB(now(), INTERVAL 10 DAY) and backup_meta_file != ''",
		mysqlcomm.UnsafeEqual(cnf.BackupType, "'"),
		mysqlcomm.UnsafeEqual(cnf.ClusterAddress, "'"),
		cnf.MysqlPort)

	sqlBuilder := sq.Select("backup_id", "backup_begin_time", "extra_fields").
		From(dbareport.ModelLocalBackupReport{}.TableName()).
		Where(whereStr).OrderBy("backup_begin_time desc").Limit(1)

	sqlStr, _, err := sqlBuilder.ToSql()
	if err != nil {
		return 0, err
	}
	logger.Log.Infof("GetLastBackupSize sql: %s", sqlStr)
	res := db.QueryRow(sqlStr)
	var backupId, backupTime, extraFieldsStr string
	if err = res.Scan(&backupId, &backupTime, &extraFieldsStr); err != nil {
		return 0, errs.WithMessagef(err, "query the last full backup size for %d", cnf.MysqlPort)
	}
	extraFields := dbareport.ExtraFields{}
	if err = json.Unmarshal([]byte(extraFieldsStr), &extraFields); err != nil {
		return 0, err
	}
	logger.Log.Infof("GetLastBackupSize for backup_id=%s, backup_type=%s, backup_time=%s extra_fields=%+v",
		backupId, cnf.BackupType, backupTime, extraFields)
	return extraFields.TotalFilesize, nil
}
