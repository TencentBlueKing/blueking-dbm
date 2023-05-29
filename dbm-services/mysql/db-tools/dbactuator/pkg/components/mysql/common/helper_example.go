package common

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// InstanceExample TODO
var InstanceExample = native.Instance{
	Host: "2.2.2.2",
	Port: 3306,
}

// InstanceObjExample TODO
var InstanceObjExample = native.InsObject{
	Host:   "1.1.1.1",
	Port:   3306,
	Socket: "/data1/mysqldata/3306/mysql.sock",
	User:   "test",
	Pwd:    "test",
}

// AccountRepl TODO
var AccountRepl = components.MySQLReplAccount{ReplUser: "repl", ReplPwd: "xxx"}

// AccountAdmin TODO
var AccountAdmin = components.MySQLAdminAccount{AdminUser: "ADMIN", AdminPwd: "xxx"}

// AccountReplExample TODO
var AccountReplExample = components.MySQLAccountParam{
	MySQLReplAccount: AccountRepl,
}

// AccountAdminExample TODO
var AccountAdminExample = components.MySQLAccountParam{
	MySQLAdminAccount: AccountAdmin,
}

// MySQLAdminReplExample TODO
var MySQLAdminReplExample = components.MySQLAccountParam{
	MySQLAdminAccount: AccountAdmin,
	MySQLReplAccount:  AccountRepl,
}

// AccountMonitorExample TODO
var AccountMonitorExample = components.MySQLAccountParam{
	MySQLMonitorAccount: components.MySQLMonitorAccount{
		MonitorUser: "monitor",
		MonitorPwd:  "monitor",
	},
}
