package pkg

import (
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"strings"
)

// MySQLSuperDynamicPrivileges 是 MySQL 8.0.0 中随动态权限框架（WL#8131）一起引入的基础动态权限，
// 用于替代 SUPER 权限。仅包含 8.0.0 即存在的 8 个权限，确保所有 8.0.x GA 版本都支持。
var MySQLSuperDynamicPrivileges = []string{
	"BINLOG_ADMIN",
	"CONNECTION_ADMIN",
	"ENCRYPTION_KEY_ADMIN",
	"GROUP_REPLICATION_ADMIN",
	"REPLICATION_SLAVE_ADMIN",
	"ROLE_ADMIN",
	"SET_USER_ID",
	"SYSTEM_VARIABLES_ADMIN",
}

// MariaDBSuperPrivileges 是 MariaDB 10.5.2 (MDEV-21743) 中从 SUPER 权限拆分出的 7 个细粒度权限。
var MariaDBSuperPrivileges = []string{
	"BINLOG ADMIN",
	"BINLOG REPLAY",
	"CONNECTION ADMIN",
	"FEDERATED ADMIN",
	"READ_ONLY ADMIN",
	"REPLICATION MASTER ADMIN",
	"REPLICATION SLAVE ADMIN",
}

// GRANTHasSuper 检测 GRANT 语句的权限列表中是否包含 SUPER 权限。
// privs 是正则捕获的权限部分，如 "SELECT, SUPER, INSERT" 或 "ALL PRIVILEGES"。
func GRANTHasSuper(privs string) bool {
	upper := strings.ToUpper(privs)
	// ALL PRIVILEGES 包含 SUPER
	if strings.Contains(upper, "ALL PRIVILEGES") {
		return true
	}
	for _, p := range strings.Split(upper, ",") {
		if strings.TrimSpace(p) == "SUPER" {
			return true
		}
	}
	return false
}

// ExpandSuperPrivileges 从 GRANT 语句中提取权限列表和 user@host，
// 如果包含 SUPER，则额外写入一条包含指定细粒度权限的 GRANT 语句。
// privileges 是要展开的权限列表（MySQL 或 MariaDB 的），logTag 用于日志标识。
// 输出的引号风格与输入保持一致。
func ExpandSuperPrivileges(stmt string, privileges []string, logTag string, w *Writers) error {
	matches := ReGrantPlain.FindStringSubmatch(strings.TrimSpace(stmt))
	if matches == nil {
		return nil
	}
	privs, _, user, host, _, style := ExtractGrantPlainFields(matches)
	if !GRANTHasSuper(privs) {
		return nil
	}
	dynamicGrant := fmt.Sprintf(
		"GRANT %s ON *.* TO %s;\n",
		strings.Join(privileges, ", "), QuoteUser(user, host, style),
	)
	logger.Info("expanding SUPER to fine-grained privileges target=%s user=%s", logTag, user+"@"+host)
	if err := w.WriteGrant(dynamicGrant); err != nil {
		logger.Error("write dynamic grant err: %v", err)
		return err
	}
	return nil
}
