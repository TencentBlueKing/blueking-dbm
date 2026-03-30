package mysql

import (
	"bufio"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"
	"fmt"
	"strings"
)

// ParseLegacyFile 解析 legacy 版本（MySQL 5.5/5.6 或 Spider 1）的备份文件。
//
// 采用单次扫描 + 累积策略：
//  1. 扫描阶段：逐行读取，每行提取 user@host 信息并累积密码和资源限制到 map 中，
//     同时将清洗后的 GRANT 语句立即写入 grant 文件。
//  2. 输出阶段：扫描完成后，根据 map 中累积的信息一次性生成所有 CREATE USER 语句。
//
// 差异点（系统用户判断、CREATE USER 生成、SUPER 展开）通过 cfg 注入。
func ParseLegacyFile(
	scanner *bufio.Scanner, path string, totalLines int, dstVer int64,
	replacer *pkg.HostReplacer, cfg *pkg.ParseConfig, w *pkg.Writers,
) error {
	ls := pkg.NewLineScanner(scanner, path, totalLines)
	defer ls.Stop()

	userMap := make(map[string]*pkg.UserEntry)
	var userOrder []string
	systemUserCount := 0

	for ls.Next() {
		line := replacer.Replace(ls.Stmt())

		if matches := pkg.ReGrantWithAuth.FindStringSubmatch(line); matches != nil {
			privs, scope, user, host, hash, rest, style := pkg.ExtractGrantWithAuthFields(matches)
			key := user + "@" + host

			if cfg.IsSystemUser(user, host) {
				if err := w.WriteSystemUser(fmt.Sprintf("%s;\n", line)); err != nil {
					logger.Error("WriteSystemUser: %v", err)
					return err
				}
				systemUserCount++
				logger.Info("skipping system/job user %s", key)
				continue
			}

			entry := getOrCreateEntry(userMap, &userOrder, key, user, host, style)
			if entry.Hash == "" {
				entry.Hash = hash
			}
			entry.Resources = entry.Resources.Merge(pkg.ParseResourceLimits(rest))

			if err := writeCleanGrant(privs, scope, user, host, rest, dstVer, cfg, w); err != nil {
				return err
			}
			continue
		}

		if matches := pkg.ReGrantPlain.FindStringSubmatch(line); matches != nil {
			privs, scope, user, host, rest, style := pkg.ExtractGrantPlainFields(matches)
			key := user + "@" + host

			if cfg.IsSystemUser(user, host) {
				if err := w.WriteSystemUser(fmt.Sprintf("%s;\n", line)); err != nil {
					logger.Error("WriteSystemUser: %v", err)
					return err
				}
				systemUserCount++
				logger.Info("skipping system/job user %s", key)
				continue
			}

			entry := getOrCreateEntry(userMap, &userOrder, key, user, host, style)
			entry.Resources = entry.Resources.Merge(pkg.ParseResourceLimits(rest))

			if err := writeCleanGrant(privs, scope, user, host, rest, dstVer, cfg, w); err != nil {
				return err
			}
			continue
		}
	}

	if err := ls.Err(); err != nil {
		logger.Error("reading backup file: %v", err)
		return fmt.Errorf("reading backup file: %w", err)
	}

	for _, key := range userOrder {
		entry := userMap[key]
		createSQL := cfg.BuildCreateFromEntry(entry, dstVer)
		if err := w.WriteCreate(createSQL); err != nil {
			logger.Error("WriteCreate for %s: %v", key, err)
			return err
		}
	}

	logger.Info("users=%d systemUserStatements=%d", len(userOrder), systemUserCount)
	return nil
}

// getOrCreateEntry 从 map 中获取或创建 UserEntry。
// 首次创建时记录顺序到 order 切片，保证输出顺序稳定。
func getOrCreateEntry(
	m map[string]*pkg.UserEntry, order *[]string, key, user, host string, style pkg.QuoteStyle,
) *pkg.UserEntry {
	if e, ok := m[key]; ok {
		return e
	}
	e := &pkg.UserEntry{User: user, Host: host, Style: style}
	m[key] = e
	*order = append(*order, key)
	return e
}

// BuildCreateFromEntryMySQL 根据累积的 UserEntry 信息生成 MySQL 的 CREATE USER 语句。
//
// 目标版本 < 5.7 时输出 GRANT USAGE 载体格式（兼容 5.5/5.6），
// 目标版本 >= 5.7 时输出 CREATE USER 格式（使用 /*!50706 IF NOT EXISTS */ hint）。
func BuildCreateFromEntryMySQL(e *pkg.UserEntry, dstVer int64) string {
	withClause := e.Resources.FormatWithClause()

	if dstVer < 5007000 {
		if e.Hash != "" {
			return fmt.Sprintf("GRANT USAGE ON *.* TO '%s'@'%s' IDENTIFIED BY PASSWORD '%s'%s;\n",
				e.User, e.Host, e.Hash, withClause)
		}
		return fmt.Sprintf("GRANT USAGE ON *.* TO '%s'@'%s'%s;\n",
			e.User, e.Host, withClause)
	}

	if e.Hash != "" {
		return fmt.Sprintf(
			"CREATE USER /*!50706 IF NOT EXISTS */ '%s'@'%s' IDENTIFIED WITH 'mysql_native_password' AS '%s'%s;\n",
			e.User, e.Host, e.Hash, withClause)
	}
	return fmt.Sprintf("CREATE USER /*!50706 IF NOT EXISTS */ '%s'@'%s'%s;\n",
		e.User, e.Host, withClause)
}

// writeCleanGrant 写入清洗后的 GRANT 语句。
//
// 清洗规则：
//   - 剥离 IDENTIFIED BY PASSWORD（由调用方通过正则分离，rest 中已不含）
//   - 剥离资源限制（已累积到 CREATE USER）
//   - 保留 GRANT OPTION
func writeCleanGrant(privs, scope, user, host, rest string, dstVer int64, cfg *pkg.ParseConfig, w *pkg.Writers) error {
	grantOption := extractGrantOption(rest)

	var withClause string
	if grantOption {
		withClause = " WITH GRANT OPTION"
	}

	grantSQL := fmt.Sprintf("GRANT %s ON %s TO '%s'@'%s'%s;\n", privs, scope, user, host, withClause)
	grantSQL = cfg.RewritePrivs(grantSQL, dstVer)
	if err := w.WriteGrant(grantSQL); err != nil {
		logger.Error("WriteGrant: %v", err)
		return err
	}
	return cfg.ExpandSuper(grantSQL, dstVer, w)
}

// extractGrantOption 检查 rest 字符串中是否包含 GRANT OPTION。
func extractGrantOption(rest string) bool {
	return strings.Contains(strings.ToUpper(rest), "GRANT OPTION")
}
