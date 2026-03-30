package mysql

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"
)

// expandSuperPrivilege 当目标版本 >= 80 且 GRANT 语句包含 SUPER 时，
// 额外写入一条包含所有 MySQL 8.0 SUPER 拆分动态权限的 GRANT 语句。
// 原有的 SUPER 权限保留不动。
func expandSuperPrivilege(stmt string, dstVer int64, w *pkg.Writers) error {
	if dstVer < 8000000 {
		return nil
	}
	return pkg.ExpandSuperPrivileges(stmt, pkg.MySQLSuperDynamicPrivileges, "MySQL 8.0+", w)
}

// rewritePrivsNoop MySQL 不需要权限改名，原样返回。
func rewritePrivsNoop(stmt string, _ int64) string {
	return stmt
}
