package spider

import "dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"

// expandSuperForSpider4 当目标版本是 Spider4（MariaDB）且 GRANT 语句包含 SUPER 时，
// 额外写入一条包含 MariaDB SUPER 拆分权限的 GRANT 语句。
// 原有的 SUPER 权限保留不动。
func expandSuperForSpider4(stmt string, dstVer int64, w *pkg.Writers) error {
	if dstVer < 4000000 {
		return nil
	}
	return pkg.ExpandSuperPrivileges(stmt, pkg.MariaDBSuperPrivileges, "MariaDB/Spider4", w)
}

// mariaDBPrivAliases MariaDB 10.5.2 (MDEV-21743) 重命名的权限。
// SHOW GRANTS 返回新名，但 GRANT 旧名仍可执行。
// 在写入 grant 文件时统一为新名，避免 verify 阶段字符串不匹配。
var mariaDBPrivAliases = map[string]string{
	"REPLICATION CLIENT": "BINLOG MONITOR",
	"REPLICATION SLAVE":  "REPLICATION REPLICA",
}

// rewritePrivsForSpider 当目标版本是 Spider 4 (MariaDB 10.5+) 时，
// 将 GRANT 语句中的旧权限名替换为新名。
func rewritePrivsForSpider(stmt string, dstVer int64) string {
	if dstVer < 4000000 {
		return stmt
	}
	for old, new_ := range mariaDBPrivAliases {
		stmt = pkg.ReplacePrivName(stmt, old, new_)
	}
	return stmt
}
