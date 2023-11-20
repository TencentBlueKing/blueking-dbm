package components

import (
	"fmt"
	"strings"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

// MySQLAccountParam TODO
type MySQLAccountParam struct {
	MySQLAdminAccount
	MySQLMonitorAccount
	MySQLMonitorAccessAllAccount
	MySQLReplAccount
	MySQLDbBackupAccount
	MySQLYwAccount
}

// ProxyAccountParam TODO
type ProxyAccountParam struct {
	ProxyAdminUser string `json:"proxy_admin_user,omitempty"` // proxy admin user
	ProxyAdminPwd  string `json:"proxy_admin_pwd,omitempty"`  // proxy admin pwd
}

// TdbctlAccoutParam TODO
type TdbctlAccoutParam struct {
	TdbctlUser string `json:"tdbctl_user,omitempty"`
	TdbctlPwd  string `json:"tdbctl_pwd,omitempty"`
}

var allPriv = []string{"ALL PRIVILEGES"}
var ywUserPriv = []string{"SELECT", "CREATE", "RELOAD", "PROCESS", "SHOW DATABASES", "REPLICATION CLIENT"}
var backupUserPriv = []string{"SELECT", "RELOAD", "PROCESS", "SHOW DATABASES", "REPLICATION CLIENT", "SHOW VIEW",
	"TRIGGER", "EVENT", "SUPER"}
var backupUserPriv80 = []string{"SELECT", "RELOAD", "PROCESS", "SHOW DATABASES", "REPLICATION CLIENT", "SHOW VIEW",
	"TRIGGER", "EVENT", "SUPER", "BACKUP_ADMIN"} // SUPER is deprecated
var replUserPriv = []string{"REPLICATION SLAVE", "REPLICATION CLIENT"}
var monitorUserPriv = []string{"SELECT", "RELOAD", "PROCESS", "SHOW DATABASES", "SUPER", "REPLICATION CLIENT",
	"SHOW VIEW", "EVENT", "TRIGGER", "CREATE TABLESPACE"}
var monitorAccessallPriv = []string{"SELECT,INSERT,DELETE"}

// MySQLAccountPrivs TODO
type MySQLAccountPrivs struct {
	User       string
	PassWd     string
	AuthString string // 也可以直接授权 加密的密码
	WithGrant  bool
	PrivParis  []PrivPari
	// 系统账户默认对象 *.*
	AccessObjects []string // %,localhost
}

// PrivPari TODO
type PrivPari struct {
	Object string   // 对那个库授权
	Privs  []string // SELECT, RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT, SHOW VIEW,EVENT,TRIGGER
}

// useAuthString 使用加密之后的密码
// 传入的密码是空,但是AuthString 不是空
func (p *MySQLAccountPrivs) useAuthString() bool {
	return util.StrIsEmpty(p.PassWd) && !util.StrIsEmpty(p.AuthString)
}

// GenerateInitSql TODO
// 兼容spider授权的情况
func (p *MySQLAccountPrivs) GenerateInitSql(version string) (initPrivSqls []string) {
	var needCreate bool = mysqlutil.MySQLVersionParse(version) >= mysqlutil.MySQLVersionParse("8.0") &&
		!strings.Contains(version, "tspider")
	withGrant := ""
	encr := "BY"
	pwd := p.PassWd
	if p.useAuthString() {
		encr = "AS"
		pwd = p.AuthString
	}
	if p.WithGrant {
		withGrant = "WITH GRANT OPTION"
	}
	for _, accHost := range p.AccessObjects {
		for _, pp := range p.PrivParis {
			if needCreate {
				initPrivSqls = append(initPrivSqls, fmt.Sprintf(
					"CREATE USER IF NOT EXISTS  %s@'%s'  IDENTIFIED WITH mysql_native_password  %s '%s'", p.User, accHost, encr, pwd))
				initPrivSqls = append(initPrivSqls, fmt.Sprintf("GRANT %s ON %s TO %s@'%s' %s;", strings.Join(pp.Privs, ","),
					pp.Object, p.User, accHost, withGrant))
			} else {
				initPrivSqls = append(initPrivSqls, fmt.Sprintf("GRANT %s ON %s TO %s@'%s'  IDENTIFIED %s '%s' %s;",
					strings.Join(pp.Privs, ","), pp.Object, p.User, accHost, encr, pwd, withGrant))
			}
		}
	}
	return
}

// MySQLAdminAccount TODO
type MySQLAdminAccount struct {
	// mysql admin 账户，环境变量 GENERAL_ACCOUNT_admin_user
	AdminUser string `json:"admin_user,omitempty" env:"GENERAL_ACCOUNT_admin_user"`
	// mysql admin 密码，环境变量 GENERAL_ACCOUNT_admin_pwd
	AdminPwd string `json:"admin_pwd,omitempty" env:"GENERAL_ACCOUNT_admin_pwd,unset"`
}

// GetAccountPrivs TODO
func (m MySQLAdminAccount) GetAccountPrivs(localIp string) MySQLAccountPrivs {
	return MySQLAccountPrivs{
		User:   m.AdminUser,
		PassWd: m.AdminPwd,
		PrivParis: []PrivPari{
			{
				Object: "*.*",
				Privs:  allPriv,
			},
		},
		WithGrant:     true,
		AccessObjects: []string{"localhost", localIp},
	}
}

// MySQLMonitorAccount TODO
// GRANT SELECT, RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT,
// SHOW VIEW,EVENT,TRIGGER, CREATE TABLESPACE ON *.* TO '%s'@'%s' IDENTIFIED BY '%s'"
type MySQLMonitorAccount struct {
	// mysql monitor 账户，环境变量 GENERAL_ACCOUNT_monitor_user
	MonitorUser string `json:"monitor_user,omitempty" env:"GENERAL_ACCOUNT_monitor_user"`
	// mysql monitor 密码，环境变量 GENERAL_ACCOUNT_monitor_pwd
	MonitorPwd string `json:"monitor_pwd,omitempty" env:"GENERAL_ACCOUNT_monitor_pwd,unset"`
}

// GetAccountPrivs TODO
func (m MySQLMonitorAccount) GetAccountPrivs(grantHosts ...string) MySQLAccountPrivs {
	p := MySQLAccountPrivs{
		User:   m.MonitorUser,
		PassWd: m.MonitorPwd,
		PrivParis: []PrivPari{
			{
				Object: "*.*",
				Privs:  monitorUserPriv,
			},
			{
				Object: fmt.Sprintf("%s.*", native.INFODBA_SCHEMA),
				Privs:  allPriv,
			},
		},
		WithGrant:     false,
		AccessObjects: []string{"localhost"},
	}
	p.AccessObjects = append(p.AccessObjects, grantHosts...)
	return p
}

// MySQLMonitorAccessAllAccount TODO
type MySQLMonitorAccessAllAccount struct {
	MonitorAccessAllUser string `json:"monitor_access_all_user,omitempty"` // mysql monitor@%
	MonitorAccessAllPwd  string `json:"monitor_access_all_pwd,omitempty"`  // mysql monitor@% 密码
}

// GetAccountPrivs TODO
func (m MySQLMonitorAccessAllAccount) GetAccountPrivs(grantHosts ...string) MySQLAccountPrivs {
	p := MySQLAccountPrivs{
		User:   m.MonitorAccessAllUser,
		PassWd: m.MonitorAccessAllPwd,
		PrivParis: []PrivPari{
			{
				Object: fmt.Sprintf("%s.*", native.INFODBA_SCHEMA),
				Privs:  monitorAccessallPriv,
			},
		},
		AccessObjects: []string{"%"},
	}
	p.AccessObjects = append(p.AccessObjects, grantHosts...)
	return p
}

// MySQLReplAccount TODO
// "GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO %s@%s IDENTIFIED BY '%s';"
type MySQLReplAccount struct {
	// repl user, 环境变量 GENERAL_ACCOUNT_repl_user
	ReplUser string `json:"repl_user,omitempty" env:"GENERAL_ACCOUNT_repl_user"`
	// repl pwd, 环境变量 GENERAL_ACCOUNT_repl_pwd
	ReplPwd string `json:"repl_pwd,omitempty" env:"GENERAL_ACCOUNT_repl_pwd,unset"`
}

// GetAccountPrivs TODO
func (m MySQLReplAccount) GetAccountPrivs(grantHosts ...string) MySQLAccountPrivs {
	return MySQLAccountPrivs{
		User:   m.ReplUser,
		PassWd: m.ReplPwd,
		PrivParis: []PrivPari{
			{
				Object: "*.*",
				Privs:  replUserPriv,
			},
		},
		WithGrant:     false,
		AccessObjects: grantHosts,
	}
}

// MySQLDbBackupAccount TODO
type MySQLDbBackupAccount struct {
	DbBackupUser string `json:"backup_user,omitempty"` // dbbackup user
	DbBackupPwd  string `json:"backup_pwd,omitempty"`  // dbbackup pwd
}

// GetAccountPrivs 获取备份语句
// 如果是 mysql 8.0，grant 需要 BACKUP_ADMIN 权限
func (m MySQLDbBackupAccount) GetAccountPrivs(is80 bool, grantHosts ...string) MySQLAccountPrivs {
	privPairs := []PrivPari{
		{Object: "*.*", Privs: backupUserPriv},
		{
			Object: fmt.Sprintf("%s.*", native.INFODBA_SCHEMA),
			Privs:  allPriv,
		},
	}
	if is80 {
		privPairs = []PrivPari{
			{Object: "*.*", Privs: backupUserPriv80},
			{
				Object: fmt.Sprintf("%s.*", native.INFODBA_SCHEMA),
				Privs:  allPriv,
			},
		}
	}
	return MySQLAccountPrivs{
		User:          m.DbBackupUser,
		PassWd:        m.DbBackupPwd,
		PrivParis:     privPairs,
		WithGrant:     false,
		AccessObjects: grantHosts,
	}
}

// MySQLYwAccount TODO
// SELECT, CREATE, RELOAD, PROCESS, SHOW DATABASES, REPLICATION CLIENT localhost
type MySQLYwAccount struct {
	YwUser string `json:"yw_user,omitempty" env:"GENERAL_ACCOUNT_yw_user"`     // yw user
	YwPwd  string `json:"yw_pwd,omitempty" env:"GENERAL_ACCOUNT_yw_pwd,unset"` // yw pwd
}

// GetAccountPrivs TODO
func (m MySQLYwAccount) GetAccountPrivs() MySQLAccountPrivs {
	return MySQLAccountPrivs{
		User:   m.YwUser,
		PassWd: m.YwPwd,
		PrivParis: []PrivPari{
			{
				Object: "*.*",
				Privs:  ywUserPriv,
			},
		},
		WithGrant:     false,
		AccessObjects: []string{"localhost"},
	}
}

// TBinlogDumperAccoutParam TODO
type TBinlogDumperAccoutParam struct {
	TBinlogDumperUser string `json:"tbinlogdumper_admin_user,omitempty"`
	TBinlogDumperPwd  string `json:"tbinlogdumper_admin_pwd,omitempty"`
}

// GetAccountPrivs TODO
func (m TBinlogDumperAccoutParam) GetAccountPrivs(localIp string) MySQLAccountPrivs {
	return MySQLAccountPrivs{
		User:   m.TBinlogDumperUser,
		PassWd: m.TBinlogDumperPwd,
		PrivParis: []PrivPari{
			{
				Object: "*.*",
				Privs:  allPriv,
			},
		},
		WithGrant:     true,
		AccessObjects: []string{"localhost", localIp},
	}
}
