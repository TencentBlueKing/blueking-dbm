package checker

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"

	"github.com/jmoiron/sqlx"
)

type userRow struct {
	AuthString     string `db:"auth_string"`
	MaxQuestions   int    `db:"max_questions"`
	MaxUpdates     int    `db:"max_updates"`
	MaxConnections int    `db:"max_connections"`
	MaxUserConns   int    `db:"max_user_connections"`
}

// CheckAccountOnTarget 检查 create_user 文件中的一条语句对应的账号在目标 DB 上的状态。
//
// 支持的语句格式：
//   - CREATE USER [IF NOT EXISTS] 'user'@'host' IDENTIFIED WITH 'plugin' AS 'hash' ...  (5.7/8.0)
//   - CREATE USER [IF NOT EXISTS] 'user'@'host' IDENTIFIED BY PASSWORD 'hash' ...       (5.5/5.6)
//   - CREATE USER [IF NOT EXISTS] 'user'@'host'                                         (无密码用户)
//   - GRANT USAGE ON *.* TO 'user'@'host' IDENTIFIED BY PASSWORD 'hash' ...             (5.5/5.6)
//   - GRANT USAGE ON *.* TO 'user'@'host'                                               (无密码用户)
//
// 返回值：
//   - exists: 账号是否存在
//   - passwordMatch: 密码 hash 是否一致（账号不存在时为 false）
//   - resourceMatch: 资源限制是否一致（账号不存在时为 false）
//   - err: 解析或查询错误
func CheckAccountOnTarget(
	ctx context.Context, conn *sqlx.Conn, stmt string, dstVer int64,
) (exists, passwordMatch, resourceMatch bool, err error) {
	user, host, hash, rest, parseErr := parseCreateStmt(stmt)
	if parseErr != nil {
		logger.Error("parseCreateStmt: %v", parseErr)
		return false, false, false, parseErr
	}

	stmtLimits := pkg.ParseResourceLimits(rest)

	row, queryErr := queryUserRow(ctx, conn, user, host, dstVer)
	if queryErr != nil {
		logger.Error("queryUserRow %s@%s: %v", user, host, queryErr)
		return false, false, false, queryErr
	}
	if row == nil {
		return false, false, false, nil
	}

	pwMatch := row.AuthString == hash
	rlMatch := row.MaxQuestions == stmtLimits.MaxQuestions &&
		row.MaxUpdates == stmtLimits.MaxUpdates &&
		row.MaxConnections == stmtLimits.MaxConnections &&
		row.MaxUserConns == stmtLimits.MaxUserConns

	return true, pwMatch, rlMatch, nil
}

// parseCreateStmt 从 CREATE USER 或 GRANT USAGE 语句中提取 user、host、hash 和 rest。
func parseCreateStmt(stmt string) (user, host, hash, rest string, err error) {
	stmt = strings.TrimSuffix(strings.TrimSpace(stmt), ";")

	if matches := pkg.ReCreateUser.FindStringSubmatch(stmt); matches != nil {
		user, host, _, hash, rest, _ = pkg.ExtractCreateUserFields(matches)
		return
	}

	if matches := pkg.ReCreateUserLegacy.FindStringSubmatch(stmt); matches != nil {
		user, host, hash, rest, _ = pkg.ExtractCreateUserLegacyFields(matches)
		return
	}

	if matches := pkg.ReCreateUserPlain.FindStringSubmatch(stmt); matches != nil {
		user, host, rest, _ = pkg.ExtractCreateUserPlainFields(matches)
		hash = ""
		return
	}

	if matches := pkg.ReGrantWithAuth.FindStringSubmatch(stmt); matches != nil {
		_, _, user, host, hash, rest, _ = pkg.ExtractGrantWithAuthFields(matches)
		return
	}

	if matches := pkg.ReGrantPlain.FindStringSubmatch(stmt); matches != nil {
		privs, _, u, h, r, _ := pkg.ExtractGrantPlainFields(matches)
		if strings.EqualFold(strings.TrimSpace(privs), "USAGE") {
			user, host, hash, rest = u, h, "", r
			return
		}
	}

	err = fmt.Errorf("statement does not match CREATE USER or GRANT USAGE: %s", stmt)
	logger.Error("%v", err)
	return
}

// queryUserRow 查询 mysql.user 表获取账号信息。
// 如果账号不存在返回 (nil, nil)。
func queryUserRow(ctx context.Context, conn *sqlx.Conn, user, host string, dstVer int64) (*userRow, error) {
	var authCol string
	if dstVer >= 5007000 {
		authCol = "authentication_string"
	} else {
		authCol = "Password"
	}

	query := fmt.Sprintf(
		"SELECT %s AS auth_string, max_questions, max_updates, max_connections, max_user_connections "+
			"FROM mysql.user WHERE User = ? AND Host = ?",
		authCol,
	)

	var row userRow
	if err := conn.QueryRowxContext(ctx, query, user, host).StructScan(&row); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		logger.Error("query mysql.user for %s@%s: %v", user, host, err)
		return nil, fmt.Errorf("query mysql.user for %s@%s: %w", user, host, err)
	}
	return &row, nil
}
