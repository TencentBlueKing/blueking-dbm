package mysql

import (
	"bufio"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"
	"fmt"
	"strings"
)

// ParseModernFile 解析 modern 版本（MySQL 5.7/8.0 或 Spider 3/4）的备份文件。
//
// 该版本的特征：CREATE USER 语句携带认证信息，GRANT 语句为纯授权不含密码。
// 差异点（系统用户判断、IF NOT EXISTS 语法、SUPER 展开、未识别语句处理）通过 cfg 注入。
func ParseModernFile(
	scanner *bufio.Scanner, path string, totalLines int, dstVer int64,
	replacer *pkg.HostReplacer, cfg *pkg.ParseConfig, w *pkg.Writers,
) error {
	userCount := 0
	systemUserCount := 0
	lastUser := ""

	ls := pkg.NewLineScanner(scanner, path, totalLines)
	defer ls.Stop()

	for ls.Next() {
		stmt := replacer.Replace(ls.Stmt())

		if matches := pkg.ReCreateUser.FindStringSubmatch(stmt); matches != nil {
			if err := handleModernCreateUser(stmt, matches, cfg, &lastUser, &userCount, &systemUserCount, w); err != nil {
				logger.Error("handleModernCreateUser: %v", err)
				return err
			}
			continue
		}

		if matches := pkg.ReGrantPlain.FindStringSubmatch(stmt); matches != nil {
			if err := handleModernGrant(stmt, matches, dstVer, cfg, &systemUserCount, w); err != nil {
				logger.Error("handleModernGrant: %v", err)
				return err
			}
			continue
		}

		if strings.EqualFold(strings.TrimSuffix(stmt, ";"), "FLUSH PRIVILEGES") {
			logger.Info("skipping FLUSH PRIVILEGES at line %d", ls.LineNo())
			continue
		}

		if cfg.StrictUnrecognized {
			err := fmt.Errorf("unrecognized statement at line %d: %s", ls.LineNo(), stmt)
			logger.Error("%v", err)
			return err
		}
		logger.Warn("unrecognized statement, skipping line=%d stmt=%s", ls.LineNo(), stmt)
	}

	if err := ls.Err(); err != nil {
		logger.Error("reading backup file: %v", err)
		return fmt.Errorf("reading backup file: %w", err)
	}

	logger.Info("users=%d systemUserStatements=%d", userCount, systemUserCount)
	return nil
}

// handleModernCreateUser 处理 modern 格式的 CREATE USER 语句。
// 系统用户写入独立文件，普通用户通过 cfg.AddIfNotExists 加工后写入 create 文件。
func handleModernCreateUser(
	stmt string, matches []string, cfg *pkg.ParseConfig,
	lastUser *string, userCount *int, systemUserCount *int, w *pkg.Writers,
) error {
	user, host, _ := pkg.ExtractUserHost(matches, 1)
	key := user + "@" + host

	if cfg.IsSystemUser(user, host) {
		if err := w.WriteSystemUser(fmt.Sprintf("%s;\n", stmt)); err != nil {
			logger.Error("WriteSystemUser: %v", err)
			return err
		}
		*systemUserCount++
		logger.Info("skipping system/job user %s", key)
		return nil
	}

	if key != *lastUser {
		*userCount++
		*lastUser = key
	}

	outStmt := cfg.AddIfNotExists(stmt)
	if err := w.WriteCreate(fmt.Sprintf("%s;\n", outStmt)); err != nil {
		logger.Error("WriteCreate: %v", err)
		return err
	}
	return nil
}

// handleModernGrant 处理 modern 格式的纯 GRANT 语句。
// 系统用户写入独立文件，普通用户写入 grant 文件并通过 cfg.ExpandSuper 展开 SUPER 权限。
func handleModernGrant(
	stmt string, matches []string, dstVer int64, cfg *pkg.ParseConfig,
	systemUserCount *int, w *pkg.Writers,
) error {
	_, _, user, host, _, _ := pkg.ExtractGrantPlainFields(matches)

	if cfg.IsSystemUser(user, host) {
		if err := w.WriteSystemUser(fmt.Sprintf("%s;\n", stmt)); err != nil {
			logger.Error("WriteSystemUser: %v", err)
			return err
		}
		*systemUserCount++
		logger.Info("skipping system/job user grant user=%s", user+"@"+host)
		return nil
	}

	stmt = cfg.RewritePrivs(stmt, dstVer)
	if err := w.WriteGrant(fmt.Sprintf("%s;\n", stmt)); err != nil {
		logger.Error("WriteGrant: %v", err)
		return err
	}
	return cfg.ExpandSuper(stmt, dstVer, w)
}

// AddIfNotExistsHint 给 CREATE USER 语句加上 /*!50706 IF NOT EXISTS */ hint（MySQL 专用）。
func AddIfNotExistsHint(stmt string) string {
	upper := strings.ToUpper(stmt)
	if strings.Contains(upper, "IF NOT EXISTS") {
		return stmt
	}
	return pkg.ReCreateUserPrefix.ReplaceAllString(stmt, "CREATE USER /*!50706 IF NOT EXISTS */ ")
}

// AddIfNotExistsDirect 给 CREATE USER 语句加上直接的 IF NOT EXISTS（Spider 专用）。
func AddIfNotExistsDirect(stmt string) string {
	upper := strings.ToUpper(stmt)
	if strings.Contains(upper, "IF NOT EXISTS") {
		return stmt
	}
	return pkg.ReCreateUserPrefix.ReplaceAllString(stmt, "CREATE USER IF NOT EXISTS ")
}
