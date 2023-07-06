/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dbloader

import (
	"fmt"
	"path"
	"path/filepath"
	"regexp"
	"runtime/debug"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// RepairUserAdmin TODO
func (x *Xtrabackup) RepairUserAdmin(user, password string) error {
	/*
		sql := fmt.Sprintf(
			"UPDATE `mysql`.`user` SET `authentication_string`=password('%s') WHERE `user`='%s'",
			password, user,
		)
		sql = fmt.Sprintf("ALTER USER %s@'localhost' IDENTIFIED WITH mysql_native_password BY '%s'", user, password)
	*/
	localHosts := []string{"localhost", "127.0.0.1", x.SrcBackupHost} // 这些是合法的 admin host
	localHostsUnsafe := mysqlutil.UnsafeIn(localHosts, "'")           // 不在这些列表里的 admin host 将会被 DELETE
	adminHostsSQL := fmt.Sprintf("SELECT `host` FROM `mysql`.`user` where `user`='%s'", user)
	var adminUserHosts []string
	if adminHosts, err := x.dbWorker.QueryOneColumn("host", adminHostsSQL); err != nil {
		return err
	} else {
		for _, h := range adminHosts {
			if cmutil.StringsHas(localHosts, h) {
				adminUserHosts = append(adminUserHosts, h)
			}
		}
	}

	sqlList := []string{"FLUSH PRIVILEGES;"}
	sqlList = append(sqlList, fmt.Sprintf("DELETE FROM `mysql`.`user` WHERE `user`='%s' AND `host` NOT IN (%s);",
		user, localHostsUnsafe))
	for _, adminHost := range adminUserHosts {
		sqlList = append(sqlList, fmt.Sprintf("ALTER USER %s@'%s' IDENTIFIED WITH mysql_native_password BY '%s';",
			user, adminHost, password))
		if adminHost == x.SrcBackupHost {
			sqlList = append(sqlList, fmt.Sprintf("UPDATE `mysql`.`user` SET `host`='%s' WHERE `user`='%s' and `host`='%s';",
				x.TgtInstance.Host, user, x.SrcBackupHost))
		}
	}
	sqlList = append(sqlList, "FLUSH PRIVILEGES;")

	logger.Info("RepairUserAdmin: %v", mysqlutil.ClearIdentifyByInSQLs(sqlList))
	if _, err := x.dbWorker.ExecMore(sqlList); err != nil {
		return err
	}
	return nil
	// ALTER USER ADMIN@'localhost' IDENTIFIED BY 'auth_string';
	// SET PASSWORD FOR 'ADMIN'@'localhost' = 'auth_string';
	// ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'XXX';
	// flush privileges;
}

// RepairAndTruncateMyIsamTables TODO
func (x *Xtrabackup) RepairAndTruncateMyIsamTables() error {
	systemDbs := util.StringsRemove(native.DBSys, native.TEST_DB)
	sql := fmt.Sprintf(
		`SELECT table_schema, table_name FROM information_schema.tables `+
			`WHERE table_schema not in (%s) AND engine = 'MyISAM'`,
		mysqlutil.UnsafeIn(systemDbs, "'"),
	)

	rows, err := x.dbWorker.Db.Query(sql)
	if err != nil {
		return fmt.Errorf("query myisam tables error,detail:%w,sql:%s", err, sql)
	}
	defer rows.Close()

	wg := sync.WaitGroup{}
	errorChan := make(chan error, 1)
	finishChan := make(chan bool, 1)
	for rows.Next() {
		var db string
		var table string
		if err := rows.Scan(&db, &table); err != nil {
			return err
		}
		wg.Add(1)
		go func(worker *native.DbWorker, db, table string) {
			defer wg.Done()
			defer func() {
				if r := recover(); r != nil {
					logger.Info("panic goroutine inner error!%v;%s", r, string(debug.Stack()))
					errorChan <- fmt.Errorf("panic goroutine inner error!%v", r)
					return
				}
			}()

			sql := ""
			if db == native.TEST_DB || db == native.INFODBA_SCHEMA {
				sql = fmt.Sprintf("truncate table %s.%s", db, table)
			} else {
				sql = fmt.Sprintf("repair table %s.%s", db, table)
			}
			_, err := worker.Exec(sql)
			if err != nil {
				errorChan <- fmt.Errorf("repair myisam table error,sql:%s,error:%w", sql, err)
				return
			}
			return
		}(x.dbWorker, db, table)
	}
	go func() {
		wg.Wait()
		close(finishChan)
	}()

	select {
	case <-finishChan:
	case err := <-errorChan:
		return err
	}
	return nil
}

// RepairPrivileges TODO
func (x *Xtrabackup) RepairPrivileges() error {
	tgtHost := x.TgtInstance.Host
	myUsers := []string{"ADMIN", "sync", "repl"}

	srcHostUnsafe := mysqlutil.UnsafeEqual(x.SrcBackupHost, "'")
	tgtHostUnsafe := mysqlutil.UnsafeEqual(tgtHost, "'")
	myUsersUnsafe := mysqlutil.UnsafeIn(myUsers, "'")

	var batchSQLs []string
	// delete src host's ADMIN/sync user
	sql1 := fmt.Sprintf(
		"DELETE FROM mysql.user WHERE `user` IN (%s) AND `host` = %s;",
		myUsersUnsafe, srcHostUnsafe,
	)
	batchSQLs = append(batchSQLs, sql1)

	// update src host to new, but not ADMIN/sync/repl
	sql2s := []string{
		fmt.Sprintf(
			"UPDATE mysql.user SET `host`=%s WHERE `host`=%s AND User not in (%s);",
			tgtHostUnsafe, srcHostUnsafe, myUsersUnsafe,
		),
		fmt.Sprintf(
			"UPDATE mysql.db SET `host`=%s WHERE `host`=%s AND User not in (%s);",
			tgtHostUnsafe, srcHostUnsafe, myUsersUnsafe,
		),
		fmt.Sprintf(
			"UPDATE mysql.tables_priv SET `host`=%s WHERE `host`=%s AND User not in (%s);",
			tgtHostUnsafe, srcHostUnsafe, myUsersUnsafe,
		),
	}
	batchSQLs = append(batchSQLs, sql2s...)

	// delete src host users, but not localhost
	sql3 := fmt.Sprintf(
		"DELETE FROM mysql.user WHERE `host` IN(%s);", srcHostUnsafe,
	)
	batchSQLs = append(batchSQLs, sql3)

	// flush
	sql4 := fmt.Sprintf("flush privileges;")
	batchSQLs = append(batchSQLs, sql4)
	logger.Info("RepairPrivileges: %+v", batchSQLs)
	if _, err := x.dbWorker.ExecMore(batchSQLs); err != nil {
		return err
	}
	return nil
}

// CleanEnv 为物理备份清理本机数据目录
func (x *Xtrabackup) CleanEnv(dirs []string) error {
	// 进程应该已关闭，端口关闭
	if osutil.IsPortUp(x.TgtInstance.Host, x.TgtInstance.Port) {
		return fmt.Errorf("port %d is still opened", x.TgtInstance.Port)
	}

	var dirArray []string
	for _, v := range dirs {
		if strings.TrimSpace(x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, v, "")) == "" {
			logger.Warn(fmt.Sprintf("my.cnf %s is Emtpty!!", v))
			continue
		}
		switch v {
		case "relay-log", "relay_log":
			val, err := x.myCnf.GetRelayLogDir()
			if err != nil {
				return err
			}
			reg := regexp.MustCompile(cst.RelayLogFileMatch)
			if result := reg.FindStringSubmatch(val); len(result) == 2 {
				relaylogdir := result[1]
				dirArray = append(dirArray, "rm -rf "+relaylogdir+"/*")
			}
		case "log_bin", "log-bin":
			val, err := x.myCnf.GetMySQLLogDir()
			if err != nil {
				return err
			}
			reg := regexp.MustCompile(cst.BinLogFileMatch)
			if result := reg.FindStringSubmatch(val); len(result) == 2 {
				binlogdir := result[1]
				// TODO 所有 rm -rf 的地方都应该要检查是否可能 rm -rf / binlog.xxx 这种误删可能
				dirArray = append(dirArray, "rm -rf "+binlogdir+"/*")
			}
		case "slow_query_log_file", "slow-query-log-file":
			if val := x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, "slow_query_log_file", ""); val != "" {
				dirArray = append(dirArray, "rm -f "+val)
			}
		default:
			val := x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, v, "")
			if strings.TrimSpace(val) != "" && strings.TrimSpace(val) != "/" {
				dirArray = append(dirArray, "rm -rf "+val+"/*")
			}
		}
	}
	scripts := strings.Join(dirArray, "\n")
	logger.Info("CleanEnv: %s", scripts)
	// run with mysql os user
	if _, err := osutil.ExecShellCommand(false, scripts); err != nil {
		return err
	}
	return nil
}

// ReplaceMycnf godoc
// 物理恢复新实例的 innodb_data_file_path 等参数要保持跟原实例一致(排除 server_id,server_uuid)
func (x *Xtrabackup) ReplaceMycnf(items []string) error {
	backupMyCnfPath := x.getBackupCnfName()
	backupMyCnf, err := util.LoadMyCnfForFile(backupMyCnfPath)
	if err != nil {
		return err
	}
	bakCnfMap := backupMyCnf.SaveMySQLConfig2Object()
	var itemsExclude = []string{"server_id", "server_uuid"}
	itemMap := map[string]string{}
	for _, key := range items {
		if util.StringsHas(itemsExclude, key) {
			continue
		}
		itemMap[key] = bakCnfMap.Section[util.MysqldSec].KvMap[key]
		// sed 's///g' f > /tmp/f && cat /tmp/f > f
	}
	if len(itemMap) > 0 {
		logger.Info("ReplaceMycnf new: %v", itemMap)
		if err = x.myCnf.ReplaceValuesToFile(itemMap); err != nil {
			// x.myCnf.Load() // reload it?
			return err
		}
	}
	return nil
}

// ChangeDirOwner 修正目录属组，需要 root 权限
func (x *Xtrabackup) ChangeDirOwner(dirs []string) error {
	var commands []string
	for _, v := range dirs {
		// 如果my.cnf中没有配置这个目录, 就不做操作
		if p := x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, v, ""); p != "" {
			if filepath.IsAbs(p) {
				commands = append(commands, fmt.Sprintf("chown -R mysql %s", path.Dir(p)))
			}
			// @todo 如果是相对目录，忽略 or 报错 ?
		}
	}
	script := strings.Join(commands, "\n")
	logger.Info("ChangeDirOwner: %s", script)
	if _, err := osutil.ExecShellCommand(false, script); err != nil {
		return err
	}
	return nil
}

func (x *Xtrabackup) getBackupCnfName() string {
	return fmt.Sprintf("%s/%s", x.LoaderDir, "backup-my.cnf")
}

func (x *Xtrabackup) getSocketName() string {
	sock := x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, "socket", "/tmp/mysql.sock")
	return sock
}
