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
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// DumperGrant implement interface Dumper
type DumperGrant struct {
	cnf             *config.BackupConfig
	dbbackupHome    string
	backupStartTime time.Time
	backupEndTime   time.Time
}

func (d *DumperGrant) initConfig(mysqlVerStr string) error {
	if d.cnf == nil {
		return errors.New("logical dumper params is nil")
	}
	return nil
}

// Execute call backup privileges
func (d *DumperGrant) Execute(ctx context.Context) error {
	d.backupStartTime = cmutil.TimeToSecondPrecision(time.Now())
	defer func() {
		d.backupEndTime = cmutil.TimeToSecondPrecision(time.Now())
	}()
	if err := BackupGrant(&d.cnf.Public); err != nil {
		return err
	}
	return nil
}

// PrepareBackupMetaInfo construct metaInfo
func (d *DumperGrant) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {
	var metaInfo = dbareport.IndexContent{BinlogInfo: dbareport.BinlogStatusInfo{}}
	metaInfo.BackupBeginTime = d.backupStartTime
	metaInfo.BackupEndTime = d.backupEndTime
	metaInfo.BackupConsistentTime = d.backupStartTime
	// metaInfo.GetIsFullBackup = false
	return &metaInfo, nil
}

// BackupGrant backup grant information
func BackupGrant(cfg *config.Public) error {
	db, err := mysqlconn.InitConn(cfg)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()
	usersExclude := []string{"ADMIN", "yw", "dba_bak_all_sel", "mysql.infoschema", "mysql.session", "mysql.sys"}
	rows, err := db.Query(fmt.Sprintf("select `user`, `host` from `mysql`.`user` where `user` not in (%s)",
		mysqlcomm.UnsafeIn(usersExclude, "'")))
	if err != nil {
		logger.Log.Errorf("can't send query to Mysql server %v\n", err)
		return err
	}
	defer rows.Close()
	var user string
	var host string

	filepath := cfg.BackupDir + "/" + cfg.TargetName() + ".priv"
	// logger.Log.Info(filepath)
	file, err := os.OpenFile(filepath, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		logger.Log.Error("failed to create priv file")
		return err
	}
	defer func() {
		_ = file.Close()
	}()
	writer := bufio.NewWriter(file)

	version, verErr := mysqlconn.GetMysqlVersion(db)
	verStr, _ := util.VersionParser(version)
	if verErr != nil {
		return verErr
	}
	logger.Log.Info("mysql version :", version)
	for rows.Next() {
		err := rows.Scan(&user, &host)
		if err != nil {
			logger.Log.Error("scan backup user row failed: ", err)
			return err
		}

		var grantInfo string
		if strings.Compare(verStr, "005007000") >= 0 { // mysql.version >=5.7
			sqlString := strings.Join([]string{"show create user `", user, "`@`", host, "`"}, "")
			gRows, err := db.Query(sqlString)
			if err != nil {
				logger.Log.Warn("failed to get grants about `", user, "`@`", host, "` err:", err)
				continue
			}

			for gRows.Next() {
				err := gRows.Scan(&grantInfo)
				if err != nil {
					logger.Log.Error("scan show create user row failed: ", err)
					return err
				}
				_, err = writer.WriteString(grantInfo + ";\n")
				if err != nil {
					logger.Log.Error("write user grants failed: ", err)
					return err
				}
			}
		}

		sqlString := strings.Join([]string{"show grants for `", user, "`@`", host, "`"}, "")
		gRows, err := db.Query(sqlString)
		if err != nil {
			logger.Log.Warn("failed to get grants about `", user, "`@`", host, "` err:", err)
			continue
		}
		for gRows.Next() {
			err := gRows.Scan(&grantInfo)
			if err != nil {
				logger.Log.Error("scan show grants row failed: ", err)
				return err
			}
			_, err = writer.WriteString(grantInfo + ";\n")
			if err != nil {
				logger.Log.Error("write show grants failed: ", err)
				return err
			}
		}
	}

	_, err = writer.WriteString("FLUSH PRIVILEGES;")
	if err != nil {
		logger.Log.Error("write flush privileges failed: ", err)
		return err
	}
	err = writer.Flush()
	if err != nil {
		logger.Log.Error("flush file failed: ", err)
		return err
	}

	if strings.Compare(verStr, "005007000") >= 0 { // mysql.version >=5.7
		cmdStr := fmt.Sprintf(`sed -i 's/CREATE USER IF NOT EXISTS /CREATE USER /g' %s`, filepath)
		err := exec.Command("/bin/bash", "-c", cmdStr).Run()
		if err != nil {
			logger.Log.Error(fmt.Sprintf("run %s failed: ", cmdStr), err)
			return err
		}

		cmdStr = fmt.Sprintf(`sed -i 's/^\s*CREATE USER /CREATE USER IF NOT EXISTS /g' %s`, filepath)
		err = exec.Command("/bin/bash", "-c", cmdStr).Run()
		if err != nil {
			logger.Log.Error(fmt.Sprintf("run %s failed: ", cmdStr), err)
			return err
		}
	}
	return nil
}
