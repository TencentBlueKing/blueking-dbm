package internal

// StaticSystemUsers 定义不需要迁移的系统账号列表。
// 来源于权限服务 (blueking-dbm) clone_instance_priv 定义：
//   - mysql.session, mysql.sys, mysql.infoschema, mysql: internal/mysql/init.go
//   - mariadb.sys, PUBLIC: clone_mysql_priv.go 中 spider 4 额外排除
var StaticSystemUsers = []string{
	"mysql.session",
	"mysql.sys",
	"mysql.infoschema",
	"mysql",
	"mariadb.sys",
	"PUBLIC",
	"MONITOR",
	"gcs_admin",
	"gcs_dba",
	"repl",
	"GM",
	"sync",
	"ADMIN",
	"dba_bak_all_sel",
	"partition_yw",
	"yw",
}
