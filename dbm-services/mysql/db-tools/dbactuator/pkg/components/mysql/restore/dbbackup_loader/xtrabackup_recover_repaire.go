/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dbbackup_loader

import (
	"database/sql"
	"fmt"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"strings"
	"sync"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// RepairUserAdmin 修复 ADMIN 用户的权限，主要是host和密码
// 以 skip-grant 模式运行
func (x *Xtrabackup) RepairUserAdmin(userAdmin, password string, version string) error {
	// 这些是合法的 admin host，保留下来
	localHosts := []string{"localhost", "127.0.0.1", x.SrcBackupHost}
	adminHostsQuery := fmt.Sprintf("SELECT `host` FROM `mysql`.`user` where `user`='%s'", userAdmin)
	var dropUserHosts []string
	var keepUserHosts []string // 不在这些列表里的 admin host 将会被 DELETE
	if adminHosts, err := x.dbWorker.QueryOneColumn("host", adminHostsQuery); err != nil {
		logger.Warn("failed to query admin account '%s': %s", userAdmin, err.Error())
		if errors.Is(err, sql.ErrNoRows) || err.Error() == native.NotRowFound {
			adminAccount := components.MySQLAdminAccount{AdminUser: userAdmin, AdminPwd: password}.
				GetAccountPrivs(x.TgtInstance.Host)
			grantSql := adminAccount.GenerateInitSql(version)
			logger.Info("recreate admin user '%s': %s", userAdmin, mysqlcomm.ClearIdentifyByInSQLs(grantSql))
			if _, err = x.dbWorker.ExecMore(grantSql); err != nil {
				return err
			}
		}
		return err
	} else {
		for _, h := range adminHosts {
			if cmutil.StringsHas(localHosts, h) {
				keepUserHosts = append(keepUserHosts, h)
			} else {
				dropUserHosts = append(dropUserHosts, h)
			}
		}
		// 以下逻辑只是为为了减少出错的可能
		if !cmutil.StringsHas(keepUserHosts, x.SrcBackupHost) {
			logger.Warn("src backup host does not has %s@%s, cannot fix it for new host", userAdmin, x.SrcBackupHost)
			if cmutil.StringsHas(dropUserHosts, x.TgtInstance.Host) {
				dropUserHosts = cmutil.StringsRemove(dropUserHosts, x.TgtInstance.Host)
			}
		}
	}

	sqlList := []string{"FLUSH PRIVILEGES;"}
	if len(dropUserHosts) > 0 {
		sqlList = append(sqlList, fmt.Sprintf("DELETE FROM `mysql`.`user` WHERE `user`='%s' AND `host` IN (%s);",
			userAdmin, mysqlcomm.UnsafeIn(dropUserHosts, "'")))
		/*
			for _, h := range dropUserHosts {
				sqlList = append(sqlList, fmt.Sprintf("DROP USER IF EXISTS %s@'%s';", userAdmin, h))
			}
		*/
	}

	for _, adminHost := range keepUserHosts {
		if cmutil.MySQLVersionParse(version) < cmutil.MySQLVersionParse("5.7.6") {
			sqlList = append(sqlList, fmt.Sprintf("SET PASSWORD FOR %s@'%s' = PASSWORD('%s');",
				userAdmin, adminHost, password))
		} else {
			sqlList = append(sqlList, fmt.Sprintf("ALTER USER %s@'%s' IDENTIFIED WITH mysql_native_password BY '%s';",
				userAdmin, adminHost, password))
		}
		if adminHost == x.SrcBackupHost {
			sqlList = append(sqlList, fmt.Sprintf(
				"UPDATE `mysql`.`user` SET `host`='%s' WHERE `user`='%s' and `host`='%s';",
				x.TgtInstance.Host, userAdmin, x.SrcBackupHost))
		}
	}
	sqlList = append(sqlList, "FLUSH PRIVILEGES;")

	logger.Info("RepairUserAdmin %s: %v", userAdmin, mysqlcomm.ClearIdentifyByInSQLs(sqlList))
	if _, err := x.dbWorker.ExecMore(sqlList); err != nil {
		return err
	}
	return nil
	// ALTER USER ADMIN@'localhost' IDENTIFIED BY 'auth_string';
	// SET PASSWORD FOR 'ADMIN'@'localhost' = 'auth_string';
	// ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'XXX';
	// flush privileges;
}

// RepairMyisamTablesForMysqldb 离线修复 mysql 系统库 myisam 表
func (x *Xtrabackup) RepairMyisamTablesForMysqldb() error {
	dataDir, err := x.myCnf.GetMySQLDataDir()
	if err != nil {
		return errors.WithMessage(err, "RepairMyisamTables")
	}
	// find . -name '*.MYI' -exec /usr/local/mysql/bin/myisamchk -c -r -f -v {} \; > /tmp/repair_myisam_3306.log
	// --tmpdir=/data/dbbak --sort_buffer_size=256M --key_buffer_size=256M --read_buffer_size=2M --write_buffer_size=2M
	sysMysqldbDir := filepath.Join(dataDir, "mysql")
	repairCmdArgs := []string{
		"/usr/local/mysql/bin/myisamchk", "-c", "-r", "-f", "-v",
		fmt.Sprintf("--tmpdir=%s", filepath.Join(dataDir, "tmp")),
		"--sort_buffer_size=256M", "--key_buffer_size=256M", "--read_buffer_size=2M", "--write_buffer_size=2M",
	}
	myiFiles, _ := filepath.Glob(filepath.Join(sysMysqldbDir, "*.MYI"))
	for _, myi := range myiFiles {
		repairCmd := append(repairCmdArgs, strings.TrimSuffix(myi, ".MYI"))
		logFile := fmt.Sprintf("/tmp/repair_myisam_%d.log", x.TgtInstance.Port)
		//echoLog := fmt.Sprintf("echo '%s';", strings.Join(repairCmd, " "))
		logger.Info("myisamchk cmd: %s", strings.Join(repairCmd, " "))
		repairCmd = append(repairCmd, ">>", logFile, "2>&1")
		_, errStr, err := cmutil.ExecCommand(true, dataDir, repairCmd[0], repairCmd[1:]...)
		if err != nil {
			logger.Warn("myisamchk failed: %s(%s)", errStr, err.Error())
		}
	}
	return nil
}

// RepairNonSysMyIsamTables 修复业务的 myisam 表
func (x *Xtrabackup) RepairNonSysMyIsamTables() error {
	systemDbs := cmutil.StringsRemove(native.DBSys, native.TEST_DB)
	sqlStr := fmt.Sprintf(
		`SELECT table_schema, table_name FROM information_schema.tables `+
			`WHERE table_schema not in (%s) AND engine = 'MyISAM' AND TABLE_TYPE ='BASE TABLE'`,
		mysqlcomm.UnsafeIn(systemDbs, "'"),
	)

	rows, dbErr := x.dbWorker.Db.Query(sqlStr)
	if dbErr != nil {
		return fmt.Errorf("query myisam tables error,detail:%w,sql:%s", dbErr, sqlStr)
	}
	defer rows.Close()

	wg := sync.WaitGroup{}
	limitChan := make(chan struct{}, 4) // 控制并发
	errChan := make(chan error, 4)
	stopChan := make(chan error, 1) // close 或者往里面丢 error，都会退出
	var stopErr error
	for rows.Next() {
		select {
		case stopErr = <-errChan:
			stopErr = errors.WithMessage(stopErr, "stop repair myisam tables")
			stopChan <- stopErr
			//close(stopChan)
			break
		default:
		}

		var db string
		var table string
		if err := rows.Scan(&db, &table); err != nil {
			return errors.WithMessage(err, "query myisam tables error")
		}
		limitChan <- struct{}{}
		wg.Add(1)
		go func(worker *native.DbWorker, db, table string) {
			<-limitChan
			defer wg.Done()
			/* 如果用 close(errChan) 的写法，这里要判断 panic recover
			defer func() {
				if err := recover(); err != nil {
					stopErr = fmt.Errorf("repair myisam table panic:%s", err)
				}
			}()
			*/

			repairSql := ""
			if db == native.TEST_DB || db == native.INFODBA_SCHEMA {
				// test.conn_log, check_heartbeat, backup_report
				// sql = fmt.Sprintf("truncate table %s.%s", db, table)
			} else {
				repairSql = fmt.Sprintf("repair table %s.%s", db, table)
			}
			if repairSql == "" {
				return
			} else if _, err := worker.Exec(repairSql); err != nil {
				errChan <- fmt.Errorf("repair myisam table error,sql:%s,error:%w", repairSql, err)
				return
			}
			return
		}(x.dbWorker, db, table)
	}
	go func() {
		wg.Wait()
		close(stopChan)
	}()

	if err, ok := <-stopChan; err != nil {
		return err
	} else if !ok {
		logger.Info("repair myisam tables success")
	}
	return nil
}

// RepairPrivileges repair user host like dba_bak_all_sel,MONITOR,yw
func (x *Xtrabackup) RepairPrivileges() error {
	if x.TgtInstance.Host == x.SrcBackupHost {
		return nil
	}
	myUsers := []string{"ADMIN", "sync", "repl"}

	srcHostUnsafe := mysqlcomm.UnsafeEqual(x.SrcBackupHost, "'")
	tgtHostUnsafe := mysqlcomm.UnsafeEqual(x.TgtInstance.Host, "'")
	myUsersUnsafe := mysqlcomm.UnsafeIn(myUsers, "'")

	var batchSQLs []string
	// delete src host's ADMIN/sync user
	batchSQLs = append(batchSQLs,
		fmt.Sprintf("DELETE FROM mysql.user WHERE `user` IN (%s) AND `host` = %s;", myUsersUnsafe, srcHostUnsafe))

	// update src host to new, but not ADMIN/sync/repl
	sql2s := []string{
		fmt.Sprintf(
			"UPDATE mysql.user SET `host`=%s WHERE `host`=%s AND User NOT IN (%s);",
			tgtHostUnsafe, srcHostUnsafe, myUsersUnsafe,
		),
		fmt.Sprintf(
			"UPDATE mysql.db SET `host`=%s WHERE `host`=%s AND User NOT IN (%s);",
			tgtHostUnsafe, srcHostUnsafe, myUsersUnsafe,
		),
		fmt.Sprintf(
			"UPDATE mysql.tables_priv SET `host`=%s WHERE `host`=%s AND User NOT IN (%s);",
			tgtHostUnsafe, srcHostUnsafe, myUsersUnsafe,
		),
	}
	if cmutil.MySQLVersionParse(x.MySQLVersion) >= cmutil.MySQLVersionParse("8.0.0") {
		// mysql 8.0 的 BACKUP_ADMIN 权限记录在 mysql.global_grants 中
		sql2s = append(sql2s, fmt.Sprintf(
			"UPDATE mysql.global_grants SET `HOST`=%s WHERE `HOST`=%s AND User NOT IN (%s);",
			tgtHostUnsafe, srcHostUnsafe, myUsersUnsafe,
		))
	}

	batchSQLs = append(batchSQLs, sql2s...)
	// flush
	sql4 := fmt.Sprintf("flush privileges;")
	batchSQLs = append(batchSQLs, sql4)
	logger.Info("RepairPrivileges: %+v", batchSQLs)
	if _, err := x.dbWorker.ExecMore(batchSQLs); err != nil {
		return err
	}
	return nil
}

// cleanDirectory 为物理备份清理本机数据目录
// 如果输入的是文件，则直接删除
// 如果输入的是目录，则根据 backup 选项是否备份
func (x *Xtrabackup) cleanDirectory(backup bool) error {
	dirs := []string{
		"datadir",
		"innodb_log_group_home_dir",
		"innodb_data_home_dir",
		"relay-log",
		"log_bin",
		"tmpdir",
	}
	if x.StorageType == "tokudb" {
		dirs = []string{"tokudb_log_dir", "tokudb_data_dir", "tmpdir", "relay-log",
			"innodb_log_group_home_dir", "innodb_data_home_dir"} // replace ibdata1
	}
	// rocksdb 在自己的恢复程序里清理了

	// 进程应该已关闭，端口未关闭则报错
	if osutil.IsPortUp(x.TgtInstance.Host, x.TgtInstance.Port) {
		return fmt.Errorf("port %d is still opened", x.TgtInstance.Port)
	}
	var dirsToReset []string
	for _, v := range dirs {
		if strings.TrimSpace(x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, v, "")) == "" {
			logger.Warn(fmt.Sprintf("my.cnf %s is Emtpty!!", v))
			continue
		}
		switch v {
		case "relay-log", "relay_log":
			relayDir, err := x.myCnf.GetRelayLogDir()
			if err != nil {
				return err
			}
			dirsToReset = append(dirsToReset, relayDir)
		case "log_bin", "log-bin":
			binlogDir, _, err := x.myCnf.GetBinLogDir()
			if err != nil {
				return err
			}
			dirsToReset = append(dirsToReset, binlogDir)
		case "slow_query_log_file", "slow-query-log-file":
			if val := x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, "slow_query_log_file", ""); val != "" {
				os.Truncate(val, 0)
			}
		default:
			val := x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, v, "")
			if cmutil.FileExists(val) && !cmutil.IsDirectory(val) {
				logger.Info("Remove file %s", val)
				os.Remove(val)
			} else {
				if strings.TrimSpace(val) != "" && strings.TrimSpace(val) != "/" && strings.TrimSpace(val) != "./" {
					dirsToReset = append(dirsToReset, val)
				}
			}
		}
	}
	return ResetPath(dirsToReset, x.myCnf, backup)
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
		// 需要忽略没在 backup-my.cnf 里面的配置项
		if val, ok := bakCnfMap.Section[util.MysqldSec].KvMap[key]; ok {
			itemMap[key] = val
		} else {
			continue
		}
		// sed 's///g' f > /tmp/f && cat /tmp/f > f
	}
	if len(itemMap) > 0 {
		logger.Info("ReplaceMycnf new: %v", itemMap)
		if err = x.myCnf.ReplaceValuesToFile(itemMap); err != nil {
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

// getBackupCnfName 获取 xtrabackup 目录下的 backup-my.cnf
func (x *Xtrabackup) getBackupCnfName() string {
	return fmt.Sprintf("%s/%s", x.LoaderDir, "backup-my.cnf")
}

func (x *Xtrabackup) getSocketName() string {
	sock := x.myCnf.GetMyCnfByKeyWithDefault(util.MysqldSec, "socket", "/tmp/mysql.sock")
	return sock
}

// ResetPath clean files
// if filepath is dir, clean all files in it (file permission and owner is NOT preserved)
// if filepath is file, remove it
// this function is used to avoid "/bin/rm: Argument list too long" when using rm -rf /xxx/path/*
func ResetPath(paths []string, cnf *util.CnfFile, backup bool) error {
	if backup {
		if dataRootDir, err := cnf.GetMySQLDataRootDir(); err != nil {
			return errors.WithMessage(err, "get data root dir to reset")
		} else {
			logRootDir, err := cnf.GetMySQLLogRootDir()
			if err != nil {
				return errors.WithMessage(err, "get log root dir to reset")
			}
			if relayLogDir, _ := cnf.GetRelayLogDir(); relayLogDir != "" {
				// 一般来说 relay log 在 data root dir 下，如果不在则需要单独清理
				if !strings.Contains(dataRootDir, filepath.Base(relayLogDir)) {
					logger.Info("clean relay logDir: %s", relayLogDir)
					os.RemoveAll(relayLogDir)
					os.MkdirAll(relayLogDir, 0755)
					exec.Command("chown", "-R", "mysql:mysql", relayLogDir).Run()
				}
			}

			logger.Info("Directories to rename: [%s, %s]", dataRootDir, logRootDir)
			ts := cmutil.NewTimestampString()
			os.Rename(dataRootDir, dataRootDir+".bak"+ts)
			os.Mkdir(dataRootDir, 0755)
			os.Rename(logRootDir, logRootDir+".bak"+ts)
			os.Mkdir(logRootDir, 0755)
			logger.Info("Directories to reCreate: %v", paths)
			for _, dir := range paths {
				os.MkdirAll(dir, 0755)
			}
			exec.Command("chown", "-R", "mysql:mysql", dataRootDir).Run()
			exec.Command("chown", "-R", "mysql:mysql", logRootDir).Run()
		}
		return nil
	} else {
		logger.Info("Directories to reset: %+v", paths)
		for _, pa := range paths {
			if strings.TrimSpace(pa) == "." || strings.TrimSpace(pa) == "./" {
				return errors.Errorf("path %s is not allowed to clean", pa)
			}
			if cmutil.IsDirectory(pa) {
				logger.Info("Clean Dir: %s", pa)
				if err := cmutil.SafeRmDir(pa); err != nil {
					return errors.WithMessage(err, "clean dir")
				} else { // recreate dir
					if err = os.MkdirAll(pa, 0755); err != nil {
						return errors.WithMessage(err, "recreate dir")
					}
				}
			} else {
				logger.Info("Remove File: %s", pa)
				if err := os.RemoveAll(pa); err != nil {
					return errors.WithMessage(err, "remove file")
				}
			}
		}
		return nil
	}
}
