/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/golang/glog"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// MysqlUpgradeComp TODO
type MysqlUpgradeComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       MysqlUpgradeParam        `json:"extend"`
	upgradeRtx   `json:"-"`
}

// MysqlUpgradeParam TODO
type MysqlUpgradeParam struct {
	Host  string `json:"host"  validate:"required,ip"`
	Ports []int  `json:"ports"`
	components.Medium
	// 是否强制升级
	IsForce bool `json:"is_force"`
	// 只做升级检查
	Run bool `json:"run"`
}

// VersionInfo TODO
type VersionInfo struct {
	Version       string
	MysqlVersion  uint64
	TmysqlVersion uint64
	IsToku        bool
}

// 运行时上下文
type upgradeRtx struct {
	dbConns    map[Port]*native.DbWorker
	verMap     map[Port]VersionInfo
	sysUsers   []string
	newVersion VersionInfo
	socketMaps map[Port]string
	adminUser  string
	adminPwd   string
}

// Example subcommand example input
func (m *MysqlUpgradeComp) Example() interface{} {
	comp := MysqlUpgradeComp{
		Params: MysqlUpgradeParam{
			Host:  "127.0.0.1",
			Ports: []int{3306, 3307},
			Run:   false,
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
	return comp
}

// Init prepare run env
func (m *MysqlUpgradeComp) Init() (err error) {
	m.dbConns = make(map[Port]*native.DbWorker)
	m.verMap = make(map[Port]VersionInfo)
	m.socketMaps = make(map[Port]string)
	m.sysUsers = m.GeneralParam.GetAllSysAccount()
	m.adminUser = m.GeneralParam.RuntimeAccountParam.AdminUser
	m.adminPwd = m.GeneralParam.RuntimeAccountParam.AdminPwd
	m.newVersion = VersionInfo{
		Version:       m.Params.Pkg,
		MysqlVersion:  cmutil.MySQLVersionParse(m.Params.Pkg),
		TmysqlVersion: cmutil.TmysqlVersionParse(m.Params.Pkg),
	}
	if m.newVersion.MysqlVersion <= 0 {
		return fmt.Errorf("mysql version %s is invalid", m.Params.Pkg)
	}
	for _, port := range m.Params.Ports {
		dbConn, err := native.InsObject{
			Host: m.Params.Host,
			Port: port,
			User: m.adminUser,
			Pwd:  m.adminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		m.dbConns[port] = dbConn
		ver, err := dbConn.SelectVersion()
		if err != nil {
			logger.Error("Get version failed:%s", err.Error())
			return err
		}
		isTokudb := false
		isTokudb, err = dbConn.HasTokudb()
		if err != nil {
			logger.Error("query %d engine  failed:%s", port, err.Error())
			return err
		}
		currentVer := VersionInfo{
			Version:       ver,
			MysqlVersion:  cmutil.MySQLVersionParse(ver),
			TmysqlVersion: cmutil.TmysqlVersionParse(ver),
			IsToku:        isTokudb,
		}
		m.verMap[port] = currentVer
		if err = currentVer.canUpgrade(m.newVersion); err != nil {
			logger.Error("upgrade version check failed %s", err.Error())
			return err
		}
	}

	logger.Info("mysql upgrade init ok,new version:%d", m.newVersion.MysqlVersion)
	return nil
}

// PreCheck pre run pre check
func (m *MysqlUpgradeComp) PreCheck() (err error) {
	logger.Info("check delete user only at mysql.user table,but not delete user in mysql.user_priv ... tables")
	for port, conn := range m.dbConns {
		dirtyAccounts, err := conn.GetDeleteWithoutDropUser()
		if err != nil {
			logger.Warn("get dirty accounts on %d failed:%s", port, err.Error())
		}
		if len(dirtyAccounts) > 0 {
			logger.Warn("users have DELETE but no DROP:%v", dirtyAccounts)
		}
		pls, err := conn.ShowApplicationProcesslist(m.sysUsers)
		if err != nil {
			logger.Error("show application processlist failed:%s", err.Error())
			return err
		}
		if len(pls) > 0 {
			return fmt.Errorf("exist dirty processlist:%v in %d", pls, port)
		}
	}
	if m.Params.Run {
		if !cmutil.FileExists(m.Params.GetAbsolutePath()) {
			return fmt.Errorf("%s file not exist", m.Params.Pkg)
		}
	}
	return
}

// canUpgrade TODO
func (current *VersionInfo) canUpgrade(newVersion VersionInfo) (err error) {
	logger.Info("newvesion is %v", newVersion)
	logger.Info("currentvesion MysqlVersion  is %v", current.MysqlVersion)
	logger.Info("currentvesion TmysqlVersion is %v", current.TmysqlVersion)
	logger.Info("currentvesion IsToku is %v", current.IsToku)
	switch {
	case current.MysqlVersion < native.MYSQL_5P5P24:
		return fmt.Errorf("don't support current version: %d lower than mysql-5.5.24 to upgrade", current.MysqlVersion)
	case current.MysqlVersion > newVersion.MysqlVersion:
		return fmt.Errorf("don't allow to decrease mysql version: current version: %s,  new version: %s", current.Version,
			newVersion.Version)
	case (newVersion.MysqlVersion == current.MysqlVersion && newVersion.TmysqlVersion < current.TmysqlVersion):
		return fmt.Errorf("don't allow to decrease tmysql version: current version: %s,  new version: %s", current.Version,
			newVersion.Version)
	case newVersion.TmysqlVersion < native.TMYSQL_1P1:
		return fmt.Errorf("don't allow to upgrade to NON-TMYSQL: current version: %s, new version: %s", current.Version,
			newVersion.Version)
	case (newVersion.TmysqlVersion/1000000)-(current.TmysqlVersion/1000000) > 1:
		return fmt.Errorf("don't allow to upgrade across big versin: current version: %s, new version: %s",
			current.Version, newVersion.Version)
	case newVersion.TmysqlVersion >= native.TMYSQL_1 && current.MysqlVersion < native.MYSQL_5P1P24:
		return fmt.Errorf("don't allow to upgrade, current version: %s, new version: %s", current.Version,
			newVersion.Version)
	case newVersion.TmysqlVersion >= native.TMYSQL_2 && current.TmysqlVersion < native.TMYSQL_1:
		return fmt.Errorf("don't allow to upgrade tmysql 2.x: current version: %s, new version: %s", current.Version,
			newVersion.Version)
	case newVersion.MysqlVersion >= native.MYSQL_8P0 && current.MysqlVersion < native.MYSQL_5P70:
		return fmt.Errorf("upgrading to MySQL 8 from MySQL version <5.7 is not allowed: current version: %d, new version: %d",
			current.MysqlVersion, newVersion.MysqlVersion)
	}
	if current.IsToku && (newVersion.TmysqlVersion >= native.TMYSQL_3 || newVersion.TmysqlVersion <= native.TMYSQL_2P1P1) {
		return fmt.Errorf("current version: %s have enable tokudb, but newversion: %s don't support", current.Version,
			newVersion.Version)
	}
	if newVersion.MysqlVersion > native.MYSQL_5P5P1 && current.MysqlVersion > native.MYSQL_5P0P48 {
		return nil
	}
	return fmt.Errorf("don't allow to upgrade, current version: %s, new version: %s", current.Version,
		newVersion.Version)
}

// MysqlUpgradeCheck mysql upgrade check
func (m *MysqlUpgradeComp) MysqlUpgradeCheck() (err error) {
	for port, conn := range m.dbConns {
		currentVer := m.verMap[port]
		if currentVer.TmysqlVersion > native.TMYSQL_3 && currentVer.TmysqlVersion < native.TMySQL_3P15 {
			if err = conn.CheckInstantAddColumn(); err != nil {
				// 当前版本是tmysql 3, 且低于3.1.15。检查是否有非法在线加字段
				if !errors.Is(err, native.ErrorUsedInstantAddColumnButValid) {
					return err
				}
			}
		}
		if m.newVersion.MysqlVersion >= native.MYSQL_8P0 {
			if err = conn.CheckInstantAddColumn(); err != nil {
				return fmt.Errorf(
					"CheckInstantAddColumn failed, upgrade to %s cannot go on due to incompatibility of data dictionary: %s",
					m.newVersion.Version, err.Error())
			}
		}
		// table check
		if err = conn.CheckTableUpgrade(currentVer.MysqlVersion, m.newVersion.MysqlVersion); err != nil {
			logger.Error("check table upgrade failed %s", err.Error())
			return err
		}
	}
	return
}

// Upgrade do upgrade
func (m *MysqlUpgradeComp) Upgrade() (err error) {
	for port, conn := range m.dbConns {
		logger.Info("do upgrade and replace my.cnf for %d", port)
		if err = m.upgradeMycnf(port); err != nil {
			return err
		}
		logger.Info("do upgrade %d mysql old password", port)
		if err = m.upgradeOldPassword(conn, port); err != nil {
			return err
		}
		socket, ok := m.socketMaps[port]
		if !ok {
			return fmt.Errorf("get socket from socket map failed")
		}
		// shutfown mysql
		logger.Info("do shutdown mysql for %d", port)
		if err = computil.ShutdownMySQLBySocket(m.adminUser, m.adminPwd, socket); err != nil {
			logger.Error("shutdown mysql %d failed %s", port, err.Error())
			return err
		}
	}
	logger.Info("upgrade mysql install bin...")
	// relink mysql
	if err = m.relinkMysql(); err != nil {
		logger.Info("failed to replace mysql media %s", err.Error())
		return err
	}
	for _, port := range m.Params.Ports {
		start := computil.StartMySQLParam{
			Host:      m.Params.Host,
			Port:      port,
			Socket:    m.socketMaps[port],
			MySQLUser: m.adminUser,
			MySQLPwd:  m.adminPwd,

			MyCnfName: util.GetMyCnfFileName(port),
			MediaDir:  cst.MysqldInstallPath,
		}
		logger.Info("start mysql for %d", port)
		pid, err := start.StartMysqlInstance()
		if err != nil {
			logger.Error("start mysql %d failed %s", err.Error())
			return err
		}
		logger.Info("start mysql success,pid is %d", pid)
		logger.Error("reconnect mysql ")
		dbConn, err := native.InsObject{
			Host: m.Params.Host,
			Port: port,
			User: m.adminUser,
			Pwd:  m.adminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		m.dbConns[port] = dbConn
		// do  mysql check
		// MySQL 8.0.16后，mysql_upgrade被弃用，无须额外调用，升级操作被集成到mysqld中
		// 因此当升级版本在8.0.16以上时，mysqld成功拉起，即代表升级完成
		if m.newVersion.MysqlVersion >= native.MYSQL_8P0P16 {
			logger.Info("Upgrading to MySQL version>=8.0.16, remaining upgrade procedure is skipped.")
			return nil
		}
		logger.Info("do mysqlcheck  for %d", port)
		if err = m.mysqlCheck(dbConn, port); err != nil {
			logger.Error("do %d mysqlcheck failed %s", port, err.Error())
			return err
		}
		logger.Info("do mysql upgrade for %d", port)
		if err = m.mysqlUpgrade(dbConn, port); err != nil {
			logger.Error("do %d mysqlUpgrade failed %s", port, err.Error())
			return err
		}
		logger.Info("exec upgrade addition actions for %d", port)
		if err = m.additionalActions(dbConn, port); err != nil {
			logger.Error("do %d additionalActions failed %s", port, err.Error())
			return err
		}
	}
	return nil
}

func (m *MysqlUpgradeComp) relinkMysql() (err error) {
	// tar mysql new version  packege
	var stderr, oldlink string
	if stderr, err = osutil.StandardShellCommand(false, fmt.Sprintf("tar -axf %s -C %s", m.Params.GetAbsolutePath(),
		cst.UsrLocal)); err != nil {
		logger.Error("tar mysql new version packege failed %s,stderr%s", err.Error(), stderr)
		return err
	}
	fi, err := os.Lstat(cst.MysqldInstallPath)
	if err != nil {
		logger.Error("read /usr/local/mysql dir info failed %s", err.Error())
		return err
	}
	sc := ""
	newlink := m.Params.GePkgBaseName()
	switch mode := fi.Mode(); {
	case mode.IsDir():
		bakdir := fmt.Sprintf("mysql_%s", time.Now().Format(cst.TimeLayoutDir))
		sc = fmt.Sprintf("cd %s && mv mysql %s && ln -s %s mysql ",
			cst.UsrLocal, bakdir, newlink)
		logger.Info("move mysql dir to %s", bakdir)
	case mode&os.ModeSymlink != 0:
		oldlink, err = os.Readlink(cst.MysqldInstallPath)
		if err != nil {
			logger.Error("get old mysql link failed %s", err.Error())
			return err
		}
		logger.Info("mysql old link is %s", oldlink)
		sc = fmt.Sprintf("cd %s && unlink mysql && ln -s %s mysql ",
			cst.UsrLocal, newlink)
	default:
		return fmt.Errorf("file %s is not a dir or symlink", cst.MysqldInstallPath)
	}
	if stderr, err = osutil.StandardShellCommand(false, sc); err != nil {
		logger.Error("tar mysql new version packege failed %s,stderr%s", err.Error(), stderr)
		return err
	}
	return err
}

func (m *MysqlUpgradeComp) upgradeMycnf(port int) (err error) {
	// 获取配置文件路径
	cf := util.GetMyCnfFileName(port)
	cff, err := util.LoadMyCnfForFile(cf)
	if err != nil {
		logger.Error("load %s file failed: %s", cf, err.Error())
		return err
	}

	// 创建新的配置文件
	newfile := fmt.Sprintf("./my.cnf.%d.new", port)
	if err = prepareNewConfigFile(newfile); err != nil {
		return err
	}

	// 获取socket路径
	sck, err := cff.GetMySQLSocket()
	if err != nil {
		logger.Error("get mysql socket failed: %s", err.Error())
		return err
	}
	m.socketMaps[port] = sck
	cff.FileName = newfile

	// 更新配置
	section := util.MysqldSec
	if err = m.updateTmysqlConfig(cff, section); err != nil {
		return err
	}
	if err = m.updateMysqlConfig(cff, section); err != nil {
		return err
	}

	// 保存新配置文件
	if err = cff.SafeSaveFile(false); err != nil {
		logger.Error("write %s failed: %s", newfile, err.Error())
		return err
	}

	// 备份并替换原配置文件
	return m.backupAndReplaceConfig(cf, newfile)
}

func prepareNewConfigFile(newfile string) error {
	if cmutil.FileExists(newfile) {
		if err := os.Remove(newfile); err != nil {
			logger.Error("remove exist tmp my.cnf failed: %s", err.Error())
			return err
		}
	}
	return nil
}

func (m *MysqlUpgradeComp) updateTmysqlConfig(cff *util.CnfFile, section string) error {
	if m.newVersion.TmysqlVersion <= native.TMYSQL_1 {
		return nil
	}

	if m.newVersion.TmysqlVersion < native.TMYSQL_3 {
		cff.ReplaceValue(section, "innodb_create_use_gcs_real_format", true, "")
	}

	if m.newVersion.TmysqlVersion >= native.TMYSQL_1P4 {
		cff.ReplaceValue(section, "userstat", false, "ON")
		cff.ReplaceValue(section, "query_response_time_stats", false, "ON")
	}

	if m.newVersion.TmysqlVersion >= native.TMYSQL_2P1 {
		cff.ReplaceKeyName(section, "table_cache", "table_open_cache")
		cff.ReplaceValue(section, "performance_schema", false, "OFF")
		cff.Cfg.Section(section).DeleteKey("alter_query_log")
		cff.ReplaceValue(section, "secure_auth", false, "OFF")
	}

	return nil
}

func (m *MysqlUpgradeComp) updateMysqlConfig(cff *util.CnfFile, section string) error {
	if m.newVersion.MysqlVersion > native.MYSQL_5P1P46 {
		cff.ReplaceValue(section, "skip-name-resolve", true, "")
	}

	if m.newVersion.MysqlVersion > native.MYSQL_5P5P11 {
		cff.ReplaceValue(section, "slow_query_log", false, "1")
	}

	if m.newVersion.MysqlVersion > native.MYSQL_5P5P5 {
		cff.ReplaceValue(section, "innodb_file_format", false, "Barracuda")
	}

	if m.newVersion.MysqlVersion > native.MYSQL_5P5P1 {
		m.updateMysql551Config(cff, section)
	}

	if m.newVersion.MysqlVersion > native.MYSQL_5P1P29 {
		m.updateMysql5129Config(cff, section)
	}

	if m.newVersion.MysqlVersion > native.MYSQL_5P70 {
		m.updateMysql57Config(cff, section)
	}

	if m.newVersion.MysqlVersion > native.MYSQL_8P0 {
		m.updateMysql80Config(cff, section)
	}

	return nil
}

func (m *MysqlUpgradeComp) updateMysql551Config(cff *util.CnfFile, section string) {
	cff.ReplaceKeyName(section, "default-character-set", "character-set-server")
	cff.ReplaceKeyName(section, "log_bin_trust_routine_creators", "log_bin_trust_function_creators")
	cff.Cfg.Section(section).DeleteKey("skip-locking")
	cff.Cfg.Section(section).DeleteKey("log-long-format")
	cff.Cfg.Section(section).DeleteKey("log-update")
	cff.Cfg.Section(section).DeleteKey("safe-show-database")
}

func (m *MysqlUpgradeComp) updateMysql5129Config(cff *util.CnfFile, section string) {
	cff.ReplaceKeyName(section, "default-collation", "collation_server")
	cff.ReplaceKeyName(section, "default-table-type", "default_storage_engine")
	cff.ReplaceKeyName(section, "warnings", "log_warnings")
	cff.Cfg.Section(section).DeleteKey("delay-key-write-for-all-tables")
}

func (m *MysqlUpgradeComp) updateMysql57Config(cff *util.CnfFile, section string) {
	// Delete deprecated options
	deprecatedKeys := []string{
		"secure_auth", "loose_secure_auth", "innodb_additional_mem_pool_size",
		"innodb_create_use_gcs_real_format", "thread_concurrency", "storage_engine",
		"old_passwords", "innodb_file_io_threads",
	}
	for _, key := range deprecatedKeys {
		cff.Cfg.Section(section).DeleteKey(key)
	}

	// Replace key names
	cff.ReplaceKeyName(section, "thread_cache", "thread_cache_size")
	cff.ReplaceKeyName(section, "key_buffer", "key_buffer_size")
	cff.ReplaceKeyName(section, "log_warnings", "log_error_verbosity")

	// Set new values
	cff.ReplaceValue(section, "log_error_verbosity", false, "1")
	cff.ReplaceValue(section, "show_compatibility_56", false, "on")
	cff.ReplaceValue(section, "secure_file_priv", false, "")
	cff.ReplaceValue(section, "sync_binlog", false, "0")
}

func (m *MysqlUpgradeComp) updateMysql80Config(cff *util.CnfFile, section string) {
	// Delete deprecated options
	deprecatedKeys := []string{
		"innodb_file_format", "query_cache_size", "query_cache_type",
		"show_compatibility_56", "userstat", "query_response_time_stats",
	}
	for _, key := range deprecatedKeys {
		cff.Cfg.Section(section).DeleteKey(key)
	}

	// Set new values
	cff.ReplaceValue(section, "thread_handling", false, "2")
	cff.ReplaceValue(section, "performance_schema", false, "ON")
	cff.ReplaceValue(section, "explicit_defaults_for_timestamp", false, "OFF")
	cff.ReplaceValue(section, "default_authentication_plugin", false, "mysql_native_password")
}

func (m *MysqlUpgradeComp) backupAndReplaceConfig(cf, newfile string) error {
	bakcnf := cf + "." + time.Now().Format(cst.TimeLayoutDir)
	script := fmt.Sprintf("cp %s %s && cp %s %s", cf, bakcnf, newfile, cf)
	stderr, err := osutil.StandardShellCommand(false, script)
	if err != nil {
		logger.Error("replace my.cnf failed, stderr: %s, err: %s", stderr, err.Error())
		return err
	}
	return nil
}

func (m MysqlUpgradeComp) upgradeOldPassword(conn *native.DbWorker, port int) (err error) {
	currentVersion, ok := m.verMap[port]
	if !ok {
		return fmt.Errorf("get %d version from runtime ctx failed", port)
	}
	if !(m.newVersion.TmysqlVersion > native.TMYSQL_2 && currentVersion.MysqlVersion > native.MYSQL_5P70) {
		logger.Info("ignore upgradeOldPassword check")
		return nil
	}
	upgradeUsers := []string{}
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.AdminUser)
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.YwUser)
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.DbBackupUser)
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.MonitorUser)
	users, err := conn.GetIsOldPasswordUsers(upgradeUsers)
	if err != nil {
		logger.Error("query users have old password failed %s", err.Error())
	}
	for _, user := range users {
		pwd := ""
		switch user.User {
		case m.GeneralParam.RuntimeAccountParam.AdminUser:
			pwd = m.GeneralParam.RuntimeAccountParam.AdminPwd
		case m.GeneralParam.RuntimeAccountParam.YwUser:
			pwd = m.GeneralParam.RuntimeAccountParam.YwPwd
		case m.GeneralParam.RuntimeAccountParam.DbBackupUser:
			pwd = m.GeneralParam.RuntimeAccountParam.DbBackupPwd
		case m.GeneralParam.RuntimeAccountParam.MonitorUser:
			pwd = m.GeneralParam.RuntimeAccountParam.MonitorPwd
		}
		_, err = conn.Exec(
			"UPDATE mysql.user SET plugin = 'mysql_native_password',Password = PASSWORD('?') WHERE (User, Host) = ('?', '?')",
			pwd, user.User, user.Host)
		if err != nil {
			logger.Error("update mysql.user password failed %s", err.Error())
			return err
		}
	}
	if _, err = conn.Exec("FLUSH PRIVILEGES;"); err != nil {
		logger.Error("flush privileges failed %s", err.Error())
		return err
	}
	return err
}

func (m MysqlUpgradeComp) mysqlUpgrade(conn *native.DbWorker, port int) (err error) {
	currentVersion, ok := m.verMap[port]
	if !ok {
		return fmt.Errorf("get %d version from runtime ctx failed", port)
	}
	// safe big version, ignore mysqlcheck
	if (m.newVersion.TmysqlVersion / 1000000) == (currentVersion.TmysqlVersion / 100000) {
		logger.Info("same big tmysql version, ignore mysqlupgrade")
		return nil
	}
	// open general_log
	if errx := m.openGeneralLog(conn); err != nil {
		logger.Warn("set global general_log=on failed %s", errx.Error())
	}
	upgradeScript := ""
	switch {
	case m.newVersion.TmysqlVersion > native.TMYSQL_1P2 && m.newVersion.TmysqlVersion < native.TMYSQL_2:
		upgradeScript = fmt.Sprintf(
			"cd /usr/local/mysql && ./bin/mysql_upgrade -h%s --skip-write-binlog -i --grace-print  -P%d -u%s -p%s",
			m.Params.Host, port, m.adminUser, m.adminPwd)
	case currentVersion.MysqlVersion < native.MYSQL_5P70 && m.newVersion.MysqlVersion > native.MYSQL_5P70:
		upgradeScript = fmt.Sprintf(
			"cd /usr/local/mysql && ./bin/mysql_upgrade -h%s --skip-write-binlog --grace-print  -P%d -u%s -p%s",
			m.Params.Host, port, m.adminUser, m.adminPwd)
	default:
		upgradeScript = fmt.Sprintf("cd /usr/local/mysql && ./bin/mysql_upgrade -h%s -P%d --skip-write-binlog -u%s -p%s",
			m.Params.Host, port, m.adminUser, m.adminPwd)
	}
	upgradelog := fmt.Sprintf("upgrade-%d.log", port)
	c := osutil.ComplexCommand{
		Command:     upgradeScript,
		WriteStderr: true,
		WriteStdout: true,
		StdoutFile:  upgradelog,
		StderrFile:  upgradelog,
		Logger:      true,
	}
	alreadyUpgradeNum := 0
	var lines []string
	if err = c.Run(); err != nil {
		lines, err = m.alreadyUpgradedLines(upgradelog)
		if err != nil {
			logger.Error("analysis upgradelog  failed %s", err.Error())
			return err
		}
		alreadyUpgradeNum = len(lines)
		if alreadyUpgradeNum <= 0 {
			return fmt.Errorf("failed to mysqlupgrade,please refer to the log for details %s,err is %w", upgradelog, err)
		}
	}
	logger.Info("run mysql upgrade shell success")
	// close general_log
	if err = m.closeGeneralLog(conn); err != nil {
		logger.Error("set global general_log=off failed %s", err.Error())
		return err
	}
	logger.Info("check upgrade log ...")
	notOkScript := fmt.Sprintf(
		"cat %s |grep -vwE 'OK|Warning|Looking|Running|mysql|performance_schema|information_schema|collate_upgrade|REPAIR TABLE|Repairing tables|Pre-4.1 Password      hash found|Checking|Upgrading|Upgrade process|already'"+
			"|grep -v '^$' | wc -l", upgradelog)
	out1, err := exec.Command("/bin/bash", "-c", notOkScript).CombinedOutput()
	if err != nil {
		glog.Infof("check upgrade log failed %s", err.Error())
		return err
	}
	if num, _ := strconv.Atoi(strings.TrimSpace(string(out1))); num != 0 && alreadyUpgradeNum == 0 {
		err := fmt.Errorf("failed to mysqlupgrade, out1 is not empty, error info: %s", upgradelog)
		logger.Error(err.Error())
		return err
	}
	logger.Info("mysqlupgrade for %s#%s ok", m.Params.Host, port)
	return nil
}

// additionalActions 升级后额外的操作
func (m MysqlUpgradeComp) additionalActions(conn *native.DbWorker, port int) (err error) {
	currentVersion, ok := m.verMap[port]
	if !ok {
		return fmt.Errorf("get %d version from runtime ctx failed", port)
	}
	actuator := mysqlutil.ExecuteSqlAtLocal{
		NeedShowWarnings: true,
		Host:             m.Params.Host,
		Port:             port,
		WorkDir:          "./",
		User:             m.adminUser,
		Password:         m.adminPwd,
	}
	// 如果版本小于5.6则需要该更row的模式
	if m.newVersion.MysqlVersion < native.MYSQL_5P70 {
		changeRowFormatfile := fmt.Sprintf("convert_innodb_row_format_for_%d.sql", port)
		if cmutil.FileExists(changeRowFormatfile) {
			os.Remove(changeRowFormatfile)
		}
		fd, err := os.OpenFile(changeRowFormatfile, os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			logger.Error("open convert_innodb_row_format_for_%d.sql failed %s", port, err.Error())
			return err
		}
		defer fd.Close()
		if err = conn.ConvertInnodbRowFomart(currentVersion.Version, fd); err != nil {
			logger.Error("create convert_innodb_row_format_for_%d.sql failed %s", port, err.Error())
			return err
		}
		if err = actuator.ExecuteSqlByMySQLClientOne(changeRowFormatfile, " ", true); err != nil {
			logger.Error("execute sql by mysql client one %d.sql failed %s", port, err.Error())
			return err
		}
	}
	if currentVersion.IsToku && currentVersion.TmysqlVersion <= native.TMYSQL_2P1 &&
		m.newVersion.TmysqlVersion >= native.TMYSQL_2P1P1 {
		tokudbRenameTablesql := "rename_tokudb_table.sql"
		if cmutil.FileExists(tokudbRenameTablesql) {
			os.Remove(tokudbRenameTablesql)
		}
		fd, err := os.OpenFile(tokudbRenameTablesql, os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			logger.Error("open %d rename_tokudb_table.sql failed %s", port, err.Error())
			return err
		}
		defer fd.Close()
		if err = conn.RenameTokudbTable(currentVersion.Version, fd); err != nil {
			logger.Error("create convert_innodb_row_format_for_%d.sql failed %s", port, err.Error())
			return err
		}
		if err = actuator.ExecuteSqlByMySQLClientOne(tokudbRenameTablesql, " ", true); err != nil {
			logger.Error("execute sql by mysql client one %d.sql failed %s", port, err.Error())
			return err
		}
	}
	return nil
}

func (m MysqlUpgradeComp) alreadyUpgradedLines(upgradelog string) (lines []string, err error) {
	fd, err := os.Open(upgradelog)
	if err != nil {
		logger.Error("open mysqlcheck log failed %s", err.Error())
		return lines, err
	}
	already_upgraded := regexp.MustCompile("already upgraded")
	defer fd.Close()
	sc := bufio.NewScanner(fd)
	for sc.Scan() {
		line := sc.Text()
		if already_upgraded.MatchString(line) {
			lines = append(lines, line)
		}
	}
	return lines, nil
}

func (m MysqlUpgradeComp) openGeneralLog(conn *native.DbWorker) (err error) {
	// open general_log
	if _, err = conn.Exec("set global general_log=on;"); err != nil {
		logger.Error("set global general_log=on failed %s", err.Error())
		return err
	}
	return nil
}

func (m MysqlUpgradeComp) closeGeneralLog(conn *native.DbWorker) (err error) {
	// close  general_log
	if _, err = conn.Exec("set global general_log=off;"); err != nil {
		logger.Error("set global general_log=off failed %s", err.Error())
		return err
	}
	return nil
}

func (m MysqlUpgradeComp) mysqlCheck(conn *native.DbWorker, port int) (err error) {
	currentVersion, ok := m.verMap[port]
	if !ok {
		return fmt.Errorf("get %d version from runtime ctx failed", port)
	}
	// safe big version, ignore mysqlcheck
	if (m.newVersion.TmysqlVersion/1000000)-(currentVersion.TmysqlVersion/100000) == 0 {
		logger.Info("same big tmysql version, ignore mysqlcheck")
		return nil
	}
	// open general_log
	if err = m.openGeneralLog(conn); err != nil {
		logger.Error("set global general_log=on failed %s", err.Error())
		return err
	}
	mysqlchecklog := fmt.Sprintf("mysqlcheck-%d.log", port)
	mysqlcheckerrlog := fmt.Sprintf("mysqlcheck-%d.err", port)
	if cmutil.FileExists(mysqlchecklog) {
		if err = os.Remove(mysqlchecklog); err != nil {
			logger.Error("it already exists and needs to be deleted ,remove %s failed %s", mysqlchecklog, err.Error())
			return err
		}
	}
	checkScript := ""
	if (m.newVersion.TmysqlVersion > native.TMYSQL_1P2 && m.newVersion.TmysqlVersion < native.TMYSQL_2) ||
		(currentVersion.MysqlVersion < native.MYSQL_5P70 && m.newVersion.MysqlVersion > native.MYSQL_5P70) {
		checkScript = fmt.Sprintf(
			"cd %s && ./bin/mysqlcheck -h%s -P%d --check-upgrade --grace-print --all-databases --skip-write-binlog -u%s -p%s",
			cst.MysqldInstallPath, m.Params.Host, port, m.adminUser, m.adminPwd)
	} else {
		checkScript = fmt.Sprintf(
			"cd %s && ./bin/mysqlcheck -h%s -P%d --all-databases --skip-write-binlog --check-upgrade -u%s -p%s",
			cst.MysqldInstallPath, m.Params.Host, port, m.adminUser, m.adminPwd)
	}
	c := osutil.ComplexCommand{
		Command:     checkScript,
		Logger:      true,
		WriteStdout: true,
		StdoutFile:  mysqlchecklog,
		WriteStderr: true,
		StderrFile:  mysqlcheckerrlog,
	}
	if err = c.Run(); err != nil {
		logger.Error("run mysqlcheck failed %s", err.Error())
		return err
	}
	// close general_log
	if err = m.closeGeneralLog(conn); err != nil {
		logger.Error("set global general_log=off failed %s", err.Error())
		return err
	}
	var regs []*regexp.Regexp
	mysql_schema := regexp.MustCompile("^mysql")
	performance_schema := regexp.MustCompile("^performance_schema")
	information_schema := regexp.MustCompile("^information_schema")
	regs = append(regs, regexp.MustCompile("OK$"))
	regs = append(regs, performance_schema)
	regs = append(regs, information_schema)
	regs = append(regs, mysql_schema)
	if m.newVersion.TmysqlVersion > native.TMYSQL_1P2 {
		regs = append(regs, regexp.MustCompile("collate_upgrade"))
		regs = append(regs, regexp.MustCompile(`(?i)REPAIR TABLE`))
	}
	l, err := m.analysisMySQLCheckLog(mysqlchecklog, regs)
	if err != nil {
		return err
	}
	if len(l) > 0 {
		return fmt.Errorf("failed to mysqlcheck for %d, error info: %v", port, l)
	}
	return nil
}

// analysisMySQLCheckLog 分析mysqlcheck 的输出的结果
func (m MysqlUpgradeComp) analysisMySQLCheckLog(mysqlchecklog string, regs []*regexp.Regexp) (lines []string,
	err error) {
	fd, err := os.Open(mysqlchecklog)
	if err != nil {
		logger.Error("open mysqlcheck log failed %s", err.Error())
		return lines, err
	}
	var abnormalLines []string

	defer fd.Close()
	sc := bufio.NewScanner(fd)
	for sc.Scan() {
		line := sc.Text()
		for _, reg := range regs {
			if reg.MatchString(line) {
				goto ctn
			}
		}
		abnormalLines = append(abnormalLines, line)
	ctn:
		continue
	}
	return abnormalLines, nil
}
