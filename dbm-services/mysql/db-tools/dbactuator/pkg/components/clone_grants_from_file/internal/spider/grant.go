package spider

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"
	"fmt"
	"strings"
)

// buildPlainGrantUsage 生成无密码的 GRANT USAGE ON *.* 语句，保持原始引号风格。
func buildPlainGrantUsage(user, host string, style pkg.QuoteStyle) string {
	return fmt.Sprintf("GRANT USAGE ON *.* TO %s", pkg.QuoteUser(user, host, style))
}

// trackSpider1User 在 Spider1 场景下将语句写入 create_user 文件，并更新用户计数。
// 仅当 srcVer <= spider1MaxVersion 时调用。
func trackSpider1User(stmt, key string, lastUser *string, userCount *int, w *pkg.Writers) error {
	if err := w.WriteCreate(fmt.Sprintf("%s;\n", stmt)); err != nil {
		logger.Error("track spider1 user write create: %v", err)
		return err
	}
	if key != *lastUser {
		*userCount++
		*lastUser = key
	}
	return nil
}

// processGrant 处理 GRANT 语句，分发到带认证和不带认证两个子处理函数。
// 返回 true 表示该语句已被处理。
func processGrant(
	stmt string, srcVer, dstVer int64, lastUser *string, userCount *int, w *pkg.Writers,
) (bool, error) {
	// 先尝试匹配带认证信息的 GRANT（ReGrantWithAuth 必须在 ReGrantPlain 之前）
	if matches := pkg.ReGrantWithAuth.FindStringSubmatch(stmt); matches != nil {
		return true, processGrantWithAuth(stmt, matches, srcVer, dstVer, lastUser, userCount, w)
	}

	if matches := pkg.ReGrantPlain.FindStringSubmatch(stmt); matches != nil {
		return true, processGrantPlain(stmt, matches, srcVer, dstVer, lastUser, userCount, w)
	}

	return false, nil
}

// processGrantWithAuth 处理带 IDENTIFIED BY PASSWORD 的 GRANT 语句。
//   - GRANT USAGE ON *.*：Spider1 写入 create_user + 所有版本写入无密码 grant usage
//   - 其他 GRANT：Spider1 拆出 create_user + 原样写入 grant_priv + 展开 SUPER
func processGrantWithAuth(
	stmt string, matches []string, srcVer, dstVer int64,
	lastUser *string, userCount *int, w *pkg.Writers,
) error {
	_, _, user, host, hash, rest, style := pkg.ExtractGrantWithAuthFields(matches)
	key := user + "@" + host

	if pkg.IsGrantUsageOnAll(stmt) {
		if srcVer < 2000000 {
			if err := trackSpider1User(stmt, key, lastUser, userCount, w); err != nil {
				logger.Error("process grant with auth track spider1 user: %v", err)
				return err
			}
			logger.Info("spider1 GRANT USAGE ON *.* → create_user user=%s", key)
		}
		plainUsage := buildPlainGrantUsage(user, host, style)
		if err := w.WriteGrant(fmt.Sprintf("%s;\n", plainUsage)); err != nil {
			logger.Error("process grant with auth write plain usage: %v", err)
			return err
		}
		return nil
	}

	// 非 USAGE 的带密码 GRANT
	if srcVer < 2000000 {
		createStmt := fmt.Sprintf(
			"GRANT USAGE ON *.* TO %s IDENTIFIED BY PASSWORD '%s'",
			pkg.QuoteUser(user, host, style), hash,
		)
		if trimRest := strings.TrimSpace(rest); trimRest != "" {
			createStmt += " " + trimRest
		}
		if err := trackSpider1User(createStmt, key, lastUser, userCount, w); err != nil {
			logger.Error("process grant with auth track spider1 user (non-usage): %v", err)
			return err
		}
	}

	if err := w.WriteGrant(fmt.Sprintf("%s;\n", stmt)); err != nil {
		logger.Error("process grant with auth write grant: %v", err)
		return err
	}
	return expandSuperForSpider4(stmt, dstVer, w)
}

// processGrantPlain 处理不含认证信息的纯 GRANT 语句。
//   - GRANT USAGE ON *.*：Spider1 写入 create_user + 所有版本写入无密码 grant usage
//   - 其他 GRANT：原样写入 grant_priv + 展开 SUPER
func processGrantPlain(
	stmt string, matches []string, srcVer, dstVer int64,
	lastUser *string, userCount *int, w *pkg.Writers,
) error {
	_, _, user, host, _, style := pkg.ExtractGrantPlainFields(matches)
	key := user + "@" + host

	if pkg.IsGrantUsageOnAll(stmt) {
		if srcVer < 2000000 {
			if err := trackSpider1User(stmt, key, lastUser, userCount, w); err != nil {
				logger.Error("process grant plain track spider1 user: %v", err)
				return err
			}
			logger.Info("spider1 plain GRANT USAGE ON *.* → create_user user=%s", key)
		}
		plainUsage := buildPlainGrantUsage(user, host, style)
		if err := w.WriteGrant(fmt.Sprintf("%s;\n", plainUsage)); err != nil {
			logger.Error("process grant plain write plain usage: %v", err)
			return err
		}
		return nil
	}

	if err := w.WriteGrant(fmt.Sprintf("%s;\n", stmt)); err != nil {
		logger.Error("process grant plain write grant: %v", err)
		return err
	}
	return expandSuperForSpider4(stmt, dstVer, w)
}
