package upgrade

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func (m *MysqlUpgradeComp) StartMysql() (err error) {
	start := computil.StartMySQLParam{
		Host:      m.Params.Host,
		Port:      m.port,
		Socket:    m.socket,
		MySQLUser: m.adminUser,
		MySQLPwd:  m.adminPwd,

		MyCnfName: util.GetMyCnfFileName(m.port),
		MediaDir:  cst.MysqldInstallPath,
	}
	logger.Info("start mysql for %d", m.port)
	pid, err := start.StartMysqlInsSpecialErrlog(fmt.Sprintf("/tmp/relink-media-firsrt-start-%d.log", m.port))
	if err != nil {
		logger.Error("start mysql %d failed %s", err.Error())
		return err
	}
	logger.Info("start mysql success,pid is %d", pid)
	return nil
}

func (m *MysqlUpgradeComp) ReStartMysql() (err error) {
	start := computil.StartMySQLParam{
		Host:      m.Params.Host,
		Port:      m.port,
		Socket:    m.socket,
		MySQLUser: m.adminUser,
		MySQLPwd:  m.adminPwd,

		MyCnfName: util.GetMyCnfFileName(m.port),
		MediaDir:  cst.MysqldInstallPath,
	}
	logger.Info("do mysql restart for %d", m.port)
	pid, err := start.RestartMysqlInstance()
	if err != nil {
		logger.Error("restart mysql %d failed %s", m.port, err.Error())
		return err
	}
	logger.Info("restart mysql %d success,pid is %d", m.port, pid)
	return nil
}

func (m *MysqlUpgradeComp) UpgradePrepare() (err error) {
	port := m.port
	if !m.isSameMajorTmysqlVersion {
		logger.Info("do upgrade and replace my.cnf for %d", port)
		if err = m.upgradeMycnf(); err != nil {
			return err
		}
	}
	logger.Info("do upgrade %d mysql old password", port)
	if err = m.upgradeOldPassword(); err != nil {
		return err
	}
	// shutfown mysql
	logger.Info("do shutdown mysql for %d", port)
	if err = computil.ShutdownMySQLBySocket(m.adminUser, m.adminPwd, m.socket); err != nil {
		logger.Error("shutdown mysql %d failed %s", port, err.Error())
		return err
	}
	return nil
}

func (m *MysqlUpgradeComp) Upgrade() (err error) {
	if m.isSameMajorTmysqlVersion {
		logger.Info("same big tmysql version, skip do mysql check and upgrade")
		return nil
	}
	logger.Error("reconnect mysql for %d", m.port)
	dbConn, err := native.InsObject{
		Host: m.Params.Host,
		Port: m.port,
		User: m.adminUser,
		Pwd:  m.adminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", m.port, err.Error())
		return err
	}
	logger.Info("reconnect mysql for %d success", m.port)
	// MySQL 8.0.16后，mysql_upgrade被弃用，无须额外调用，升级操作被集成到mysqld中
	// 因此当升级版本在8.0.16以上时，mysqld成功拉起，即代表升级完成
	if m.newVersion.MysqlVersion >= native.MYSQL_8P0P16 {
		logger.Info("Upgrading to MySQL version>=8.0.16, remaining upgrade procedure is skipped.")
		return nil
	}
	// 处理分区表升级
	if m.newVersion.MysqlVersion >= native.MYSQL_5P70 && m.newVersion.MysqlVersion < native.MYSQL_8P0 {
		// logger.Info("Upgrading to MySQL version>=5.7.0, remaining upgrade procedure is skipped.")
		pdata, errx := dbConn.GetPartitionSchema()
		if errx != nil {
			logger.Error("get partition schema failed %s", errx.Error())
			return errx
		}
		if len(pdata) > 0 {
			for _, p := range pdata {
				usql := fmt.Sprintf("ALTER TABLE `%s`.`%s` UPGRADE PARTITIONING", p.TableSchema, p.TableName)
				logger.Info("upgrade partition sql: %s", usql)
				_, err = dbConn.Exec(usql)
				if err != nil {
					logger.Error("upgrade partition table %s.%s failed %s", p.TableSchema, p.TableName, err.Error())
					return err
				}
			}
		}
	}
	logger.Info("do mysqlcheck  for %d", m.port)
	if err = m.mysqlCheck(); err != nil {
		logger.Error("do %d mysqlcheck failed %s", m.port, err.Error())
		return err
	}
	logger.Info("do mysql upgrade for %d", m.port)
	if err = m.mysqlUpgrade(); err != nil {
		logger.Error("do %d mysqlUpgrade failed %s", m.port, err.Error())
		return err
	}
	logger.Info("exec upgrade addition actions for %d", m.port)
	if err = m.additionalActions(); err != nil {
		logger.Error("do %d additionalActions failed %s", m.port, err.Error())
		return err
	}
	return nil
}

func (m *MysqlUpgradeComp) upgradeMycnf() (err error) {
	// 创建新的配置文件
	newfile := fmt.Sprintf("./my.cnf.%d.new", m.port)
	if err = prepareNewConfigFile(newfile); err != nil {
		return err
	}
	m.myCnf.FileName = newfile

	// 更新配置
	section := util.MysqldSec
	if err = m.updateTmysqlConfig(m.myCnf, section); err != nil {
		return err
	}
	if err = m.updateMysqlConfig(m.myCnf, section); err != nil {
		return err
	}

	// 保存新配置文件
	if err = m.myCnf.SafeSaveFile(false); err != nil {
		logger.Error("write %s failed: %s", newfile, err.Error())
		return err
	}

	// 备份并替换原配置文件
	return m.backupAndReplaceConfig(m.myCnf.FileName, newfile)
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

func (m MysqlUpgradeComp) upgradeOldPassword() (err error) {
	currentVersion := m.versionInfo
	if !(m.newVersion.TmysqlVersion > native.TMYSQL_2 && currentVersion.MysqlVersion > native.MYSQL_5P70) {
		logger.Info("ignore upgradeOldPassword check")
		return nil
	}
	upgradeUsers := []string{}
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.AdminUser)
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.YwUser)
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.DbBackupUser)
	upgradeUsers = append(upgradeUsers, m.GeneralParam.RuntimeAccountParam.MonitorUser)
	users, err := m.dbConn.GetIsOldPasswordUsers(upgradeUsers)
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
		_, err = m.dbConn.Exec(
			"UPDATE mysql.user SET plugin = 'mysql_native_password',Password = PASSWORD('?') WHERE (User, Host) = ('?', '?')",
			pwd, user.User, user.Host)
		if err != nil {
			logger.Error("update mysql.user password failed %s", err.Error())
			return err
		}
	}
	if _, err = m.dbConn.Exec("FLUSH PRIVILEGES;"); err != nil {
		logger.Error("flush privileges failed %s", err.Error())
		return err
	}
	return err
}

func (m MysqlUpgradeComp) mysqlUpgrade() (err error) {
	currentVersion := m.versionInfo
	// safe big version, ignore mysqlcheck
	if m.isSameMajorTmysqlVersion {
		logger.Info("same big tmysql version, ignore mysqlupgrade")
		return nil
	}
	// open general_log
	if errx := m.openGeneralLog(); errx != nil {
		logger.Warn("set global general_log=on failed %s", errx.Error())
	}
	upgradeScript := ""
	switch {
	case m.newVersion.TmysqlVersion > native.TMYSQL_1P2 && m.newVersion.TmysqlVersion < native.TMYSQL_2:
		upgradeScript = fmt.Sprintf(
			"cd /usr/local/mysql && ./bin/mysql_upgrade -h%s --skip-write-binlog -i --grace-print  -P%d -u%s -p%s",
			m.Params.Host, m.port, m.adminUser, m.adminPwd)
	case currentVersion.MysqlVersion < native.MYSQL_5P70 && m.newVersion.MysqlVersion > native.MYSQL_5P70:
		upgradeScript = fmt.Sprintf(
			"cd /usr/local/mysql && ./bin/mysql_upgrade -h%s --skip-write-binlog --grace-print  -P%d -u%s -p%s",
			m.Params.Host, m.port, m.adminUser, m.adminPwd)
	default:
		upgradeScript = fmt.Sprintf("cd /usr/local/mysql && ./bin/mysql_upgrade -h%s -P%d --skip-write-binlog -u%s -p%s",
			m.Params.Host, m.port, m.adminUser, m.adminPwd)
	}
	upgradelog := fmt.Sprintf("upgrade-%d.log", m.port)
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
	if err = m.closeGeneralLog(); err != nil {
		logger.Error("set global general_log=off failed %s", err.Error())
		return err
	}
	logger.Info("check upgrade log ...")
	notOkScript := fmt.Sprintf(
		"cat %s |grep -vwE 'OK|Warning|Looking|Running|mysql|performance_schema|information_schema|collate_upgrade|REPAIR TABLE|Repairing tables|Pre-4.1 Password      hash found|Checking|Upgrading|Upgrade process|already'"+
			"|grep -v '^$' | wc -l", upgradelog)
	out1, err := exec.Command("/bin/bash", "-c", notOkScript).CombinedOutput()
	if err != nil {
		logger.Info("check upgrade log failed %s", err.Error())
		return err
	}
	if num, _ := strconv.Atoi(strings.TrimSpace(string(out1))); num != 0 && alreadyUpgradeNum == 0 {
		err := fmt.Errorf("failed to mysqlupgrade, out1 is not empty, error info: %s", upgradelog)
		logger.Error(err.Error())
		return err
	}
	logger.Info("mysqlupgrade for %s#%s ok", m.Params.Host, m.port)
	return nil
}

// additionalActions 升级后额外的操作
func (m MysqlUpgradeComp) additionalActions() (err error) {
	currentVersion := m.versionInfo
	actuator := mysqlutil.ExecuteSqlAtLocal{
		NeedShowWarnings: true,
		Host:             m.Params.Host,
		Port:             m.port,
		WorkDir:          "./",
		User:             m.adminUser,
		Password:         m.adminPwd,
	}
	// 如果版本小于5.6则需要该更row的模式
	if m.newVersion.MysqlVersion < native.MYSQL_5P70 {
		changeRowFormatfile := fmt.Sprintf("convert_innodb_row_format_for_%d.sql", m.port)
		if cmutil.FileExists(changeRowFormatfile) {
			os.Remove(changeRowFormatfile)
		}
		fd, err := os.OpenFile(changeRowFormatfile, os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			logger.Error("open convert_innodb_row_format_for_%d.sql failed %s", m.port, err.Error())
			return err
		}
		defer fd.Close()
		if err = m.dbConn.ConvertInnodbRowFomart(currentVersion.Version, fd); err != nil {
			logger.Error("create convert_innodb_row_format_for_%d.sql failed %s", m.port, err.Error())
			return err
		}
		if err = actuator.ExecuteSqlByMySQLClientOne(changeRowFormatfile, " ", true); err != nil {
			logger.Error("execute sql by mysql client one %d.sql failed %s", m.port, err.Error())
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
			logger.Error("open %d rename_tokudb_table.sql failed %s", m.port, err.Error())
			return err
		}
		defer fd.Close()
		if err = m.dbConn.RenameTokudbTable(currentVersion.Version, fd); err != nil {
			logger.Error("create convert_innodb_row_format_for_%d.sql failed %s", m.port, err.Error())
			return err
		}
		if err = actuator.ExecuteSqlByMySQLClientOne(tokudbRenameTablesql, " ", true); err != nil {
			logger.Error("execute sql by mysql client one %d.sql failed %s", m.port, err.Error())
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

func (m MysqlUpgradeComp) openGeneralLog() (err error) {
	// open general_log
	if _, err = m.dbConn.Exec("set global general_log=on;"); err != nil {
		logger.Error("set global general_log=on failed %s", err.Error())
		return err
	}
	return nil
}

func (m MysqlUpgradeComp) closeGeneralLog() (err error) {
	// close  general_log
	if _, err = m.dbConn.Exec("set global general_log=off;"); err != nil {
		logger.Error("set global general_log=off failed %s", err.Error())
		return err
	}
	return nil
}

func (m MysqlUpgradeComp) mysqlCheck() (err error) {
	currentVersion := m.versionInfo
	// safe big version, ignore mysqlcheck
	if (m.newVersion.TmysqlVersion/1000000)-(currentVersion.TmysqlVersion/100000) == 0 {
		logger.Info("same big tmysql version, ignore mysqlcheck")
		return nil
	}
	// open general_log
	if err = m.openGeneralLog(); err != nil {
		logger.Error("set global general_log=on failed %s", err.Error())
		return err
	}
	mysqlchecklog := fmt.Sprintf("mysqlcheck-%d.log", m.port)
	mysqlcheckerrlog := fmt.Sprintf("mysqlcheck-%d.err", m.port)
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
			cst.MysqldInstallPath, m.Params.Host, m.port, m.adminUser, m.adminPwd)
	} else {
		checkScript = fmt.Sprintf(
			"cd %s && ./bin/mysqlcheck -h%s -P%d --all-databases --skip-write-binlog --check-upgrade -u%s -p%s",
			cst.MysqldInstallPath, m.Params.Host, m.port, m.adminUser, m.adminPwd)
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
	if err = m.closeGeneralLog(); err != nil {
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
		return fmt.Errorf("failed to mysqlcheck for %d, error info: %v", m.port, l)
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
