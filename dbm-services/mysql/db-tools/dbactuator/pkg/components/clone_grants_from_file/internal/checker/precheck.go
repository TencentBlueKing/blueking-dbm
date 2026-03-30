package checker

import (
	"context"
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"

	"github.com/jmoiron/sqlx"
)

// PreCheckCreateUserFile 逐行读取 create_user 文件，执行所有检查后统一报错：
//   - 文件自身正确性（重复账号、不支持的认证插件）
//   - 每个账号在目标 DB 上的密码和资源限制是否一致
func PreCheckCreateUserFile(conn *sqlx.Conn, filePath string, dstVer int64) error {
	var allErrors []error

	if err := checkCreateUserFileValidity(filePath); err != nil {
		allErrors = append(allErrors, err)
	}

	if err := checkAccountsOnTarget(conn, filePath, dstVer); err != nil {
		allErrors = append(allErrors, err)
	}

	if len(allErrors) > 0 {
		for _, e := range allErrors {
			logger.Error("pre-check: %v", e)
		}
		return fmt.Errorf("pre-check failed with %d error(s): %v", len(allErrors), allErrors)
	}

	return nil
}

// checkCreateUserFileValidity 扫描 create_user 文件，检查：
//   - 同一 user@host 是否出现多次（重复条目）
//   - 是否存在 caching_sha2_password 认证插件（不支持跨版本迁移）
func checkCreateUserFileValidity(filePath string) error {
	scanner, closeFile, err := pkg.OpenFileWithScanner(filePath)
	if err != nil {
		logger.Error("open create user file %s: %v", filePath, err)
		return fmt.Errorf("open create user file: %w", err)
	}
	defer closeFile()

	ls := pkg.NewLineScanner(scanner, filePath, 0)
	defer ls.Stop()
	seen := make(map[string]int) // user@host → 首次出现的行号
	var problems []string

	for ls.Next() {
		stmt := ls.Stmt()

		user, host, _, _, parseErr := parseCreateStmt(stmt)
		if parseErr != nil {
			logger.Error("parse line %d: %v", ls.LineNo(), parseErr)
			return fmt.Errorf("parse line %d: %w", ls.LineNo(), parseErr)
		}

		key := user + "@" + host
		if firstLine, exists := seen[key]; exists {
			problems = append(problems, fmt.Sprintf(
				"line %d: duplicate CREATE USER for %s (first seen at line %d)",
				ls.LineNo(), key, firstLine,
			))
		} else {
			seen[key] = ls.LineNo()
		}

		if plugin := extractAuthPlugin(stmt); strings.EqualFold(plugin, "caching_sha2_password") {
			problems = append(problems, fmt.Sprintf(
				"line %d: unsupported auth plugin caching_sha2_password for %s",
				ls.LineNo(), key,
			))
		}
	}

	if err := ls.Err(); err != nil {
		logger.Error("reading create user file: %v", err)
		return fmt.Errorf("reading create user file: %w", err)
	}

	if len(problems) > 0 {
		for _, p := range problems {
			logger.Error("file check: %s", p)
		}
		return fmt.Errorf("pre-check failed: %d problems found in create_user file", len(problems))
	}

	logger.Info("file validity check passed, unique users=%d", len(seen))
	return nil
}

// extractAuthPlugin 从 CREATE USER 语句中提取认证插件名。
// 仅匹配 IDENTIFIED WITH 'plugin' 格式（5.7/8.0），其他格式返回空字符串。
func extractAuthPlugin(stmt string) string {
	matches := pkg.ReCreateUser.FindStringSubmatch(strings.TrimSuffix(strings.TrimSpace(stmt), ";"))
	if matches == nil {
		return ""
	}
	_, _, plugin, _, _, _ := pkg.ExtractCreateUserFields(matches)
	return plugin
}

// checkAccountsOnTarget 逐行检查 create_user 文件中每个账号在目标 DB 上的密码和资源限制是否一致。
// 账号不存在的跳过，有不一致的收集后统一报错。
func checkAccountsOnTarget(conn *sqlx.Conn, filePath string, dstVer int64) error {
	scanner, closeFile, err := pkg.OpenFileWithScanner(filePath)
	if err != nil {
		logger.Error("open create user file %s: %v", filePath, err)
		return fmt.Errorf("open create user file: %w", err)
	}
	defer closeFile()

	ls := pkg.NewLineScanner(scanner, filePath, 0)
	defer ls.Stop()
	ctx := context.Background()
	var mismatches []string

	for ls.Next() {
		line := ls.Stmt()

		exists, pwMatch, rlMatch, checkErr := CheckAccountOnTarget(ctx, conn, line, dstVer)
		if checkErr != nil {
			logger.Error("pre-check line %d: %v", ls.LineNo(), checkErr)
			return fmt.Errorf("pre-check line %d: %w", ls.LineNo(), checkErr)
		}

		if !exists {
			continue
		}

		if !pwMatch || !rlMatch {
			detail := fmt.Sprintf(
				"line %d: passwordMatch=%t resourceMatch=%t stmt=%s", ls.LineNo(), pwMatch, rlMatch, line,
			)
			mismatches = append(mismatches, detail)
		}
	}

	if err := ls.Err(); err != nil {
		logger.Error("reading create user file: %v", err)
		return fmt.Errorf("reading create user file: %w", err)
	}

	if len(mismatches) > 0 {
		for _, m := range mismatches {
			logger.Error("pre-check mismatch: %s", m)
		}
		return fmt.Errorf("pre-check failed: %d accounts have mismatched password or resource limits", len(mismatches))
	}

	logger.Info("pre-check passed, total lines=%d", ls.LineNo())
	return nil
}
