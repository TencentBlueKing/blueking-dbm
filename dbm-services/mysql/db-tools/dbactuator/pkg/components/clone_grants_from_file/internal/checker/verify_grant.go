package checker

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"

	"github.com/jmoiron/sqlx"
)

// scopeGrants 表示某个 scope 上的权限集合和 GRANT OPTION 状态。
type scopeGrants struct {
	privs       map[string]struct{}
	grantOption bool
}

// VerifyGrantPrivFile 逐行读取 grant_priv 文件，验证每条 GRANT 语句对应的权限已在目标 DB 生效。
// 使用子集检查：文件中的权限必须是目标实际权限的子集。
// 当 dstVer >= 8.0 且源权限为 ALL PRIVILEGES ON *.* 时，通过 mysql.user 系统表验证所有静态权限。
func VerifyGrantPrivFile(conn *sqlx.Conn, filePath string, dstVer int64) error {
	expected, err := buildExpectedGrants(filePath)
	if err != nil {
		return err
	}

	ctx := context.Background()
	var mismatches []string

	for userHost, scopeMap := range expected {
		parts := strings.SplitN(userHost, "@", -1)
		if len(parts) < 2 {
			logger.Error("invalid user host: %s", userHost)
			return fmt.Errorf("invalid user host: %s", userHost)
		}
		user := strings.Join(parts[:len(parts)-1], "@")
		host := parts[len(parts)-1]

		actual, queryErr := queryShowGrants(ctx, conn, user, host)
		if queryErr != nil {
			logger.Error("SHOW GRANTS FOR %s: %v", userHost, queryErr)
			return fmt.Errorf("query error: SHOW GRANTS FOR %s: %w", userHost, queryErr)
		}

		for scope, exp := range scopeMap {
			if _, isAll := exp.privs["ALL PRIVILEGES"]; isAll && scope == "*.*" && dstVer >= 8000000 {
				if missing, verifyErr := verifyAllStaticPrivs(ctx, conn, user, host); verifyErr != nil {
					return fmt.Errorf("query error: verify ALL static privs for %s: %w", userHost, verifyErr)
				} else if len(missing) > 0 {
					mismatches = append(
						mismatches, fmt.Sprintf("%s: scope *.* static privs not 'Y': %v", userHost, missing),
					)
				}

				if exp.grantOption {
					if grantPriv, verifyErr := queryGrantPriv(ctx, conn, user, host); verifyErr != nil {
						return fmt.Errorf("query error: query Grant_priv for %s: %w", userHost, verifyErr)
					} else if grantPriv != "Y" {
						mismatches = append(mismatches, fmt.Sprintf("%s: scope *.* missing GRANT OPTION", userHost))
					}
				}
				continue
			}

			act, ok := actual[scope]
			if !ok {
				mismatches = append(
					mismatches, fmt.Sprintf(
						"%s: scope %s not found in SHOW GRANTS, expected privs=%s",
						userHost, scope, formatPrivSet(exp.privs),
					),
				)
				continue
			}

			missing := checkPrivSubset(exp.privs, act.privs)
			if len(missing) > 0 {
				mismatches = append(
					mismatches, fmt.Sprintf(
						"%s: scope %s missing privs=%v", userHost, scope, missing,
					),
				)
			}

			if exp.grantOption && !act.grantOption {
				mismatches = append(
					mismatches, fmt.Sprintf(
						"%s: scope %s missing GRANT OPTION", userHost, scope,
					),
				)
			}
		}
	}

	if len(mismatches) > 0 {
		for _, m := range mismatches {
			logger.Error("verify grant mismatch: %s", m)
		}
		return fmt.Errorf("verify grant failed: %d mismatches", len(mismatches))
	}

	logger.Info("verify grant passed")
	return nil
}

// buildExpectedGrants 解析 grant_priv 文件，构建 map[user@host]map[scope]*scopeGrants。
func buildExpectedGrants(filePath string) (map[string]map[string]*scopeGrants, error) {
	scanner, closeFile, err := pkg.OpenFileWithScanner(filePath)
	if err != nil {
		logger.Error("open grant file %s: %v", filePath, err)
		return nil, fmt.Errorf("open grant file: %w", err)
	}
	defer closeFile()

	ls := pkg.NewLineScanner(scanner, filePath, 0)
	defer ls.Stop()
	result := make(map[string]map[string]*scopeGrants)

	for ls.Next() {
		line := ls.Stmt()

		matches := pkg.ReGrantPlain.FindStringSubmatch(line)
		if matches == nil {
			logger.Error("verify grant: unrecognized statement at line %d: %s", ls.LineNo(), line)
			return nil, fmt.Errorf("unrecognized statement at line %d: %s", ls.LineNo(), line)
		}

		privs, scope, user, host, rest, _ := pkg.ExtractGrantPlainFields(matches)
		normScope := normalizeScope(scope)

		if strings.EqualFold(strings.TrimSpace(privs), "USAGE") && normScope == "*.*" {
			continue
		}

		userHost := user + "@" + host
		if result[userHost] == nil {
			result[userHost] = make(map[string]*scopeGrants)
		}

		sg := result[userHost][normScope]
		if sg == nil {
			sg = &scopeGrants{privs: make(map[string]struct{})}
			result[userHost][normScope] = sg
		}

		for _, p := range parsePrivSet(privs) {
			sg.privs[p] = struct{}{}
		}
		if hasGrantOption(rest) {
			sg.grantOption = true
		}
	}

	if err := ls.Err(); err != nil {
		logger.Error("reading grant file: %v", err)
		return nil, fmt.Errorf("reading grant file: %w", err)
	}

	return result, nil
}

// queryShowGrants 执行 SHOW GRANTS FOR 'user'@'host' 并解析为 map[scope]*scopeGrants。
func queryShowGrants(ctx context.Context, conn *sqlx.Conn, user, host string) (map[string]*scopeGrants, error) {
	query := fmt.Sprintf("SHOW GRANTS FOR '%s'@'%s'", user, host)
	rows, err := conn.QueryxContext(ctx, query)
	if err != nil {
		return nil, err
	}
	defer func() { _ = rows.Close() }()

	result := make(map[string]*scopeGrants)

	for rows.Next() {
		var line string
		if err := rows.Scan(&line); err != nil {
			return nil, fmt.Errorf("scan SHOW GRANTS row: %w", err)
		}

		line = strings.TrimSuffix(strings.TrimSpace(line), ";")
		matches := pkg.ReGrantPlain.FindStringSubmatch(line)
		if matches == nil {
			continue
		}

		privs, scope, _, _, rest, _ := pkg.ExtractGrantPlainFields(matches)
		normScope := normalizeScope(scope)

		sg := result[normScope]
		if sg == nil {
			sg = &scopeGrants{privs: make(map[string]struct{})}
			result[normScope] = sg
		}

		for _, p := range parsePrivSet(privs) {
			sg.privs[p] = struct{}{}
		}
		if hasGrantOption(rest) {
			sg.grantOption = true
		}
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterating SHOW GRANTS rows: %w", err)
	}

	return result, nil
}

// verifyAllStaticPrivs 通过 mysql.user 系统表验证用户是否拥有所有静态权限。
// 动态获取所有 _priv 列，排除 Grant_priv，检查是否全部为 'Y'。
// 返回值为 'N' 的列名列表。
func verifyAllStaticPrivs(ctx context.Context, conn *sqlx.Conn, user, host string) ([]string, error) {
	cols, err := queryPrivColumns(ctx, conn)
	if err != nil {
		return nil, err
	}

	selectCols := strings.Join(cols, ", ")
	query := fmt.Sprintf("SELECT %s FROM mysql.user WHERE User = ? AND Host = ?", selectCols)

	row := conn.QueryRowxContext(ctx, query, user, host)
	result := make(map[string]interface{})
	if err := row.MapScan(result); err != nil {
		return nil, fmt.Errorf("query mysql.user for %s@%s: %w", user, host, err)
	}

	var notGranted []string
	for _, col := range cols {
		val, ok := result[col]
		if !ok {
			notGranted = append(notGranted, col)
			continue
		}

		var s string
		switch v := val.(type) {
		case []byte:
			s = string(v)
		case string:
			s = v
		default:
			s = fmt.Sprintf("%v", v)
		}

		if s != "Y" {
			notGranted = append(notGranted, col)
		}
	}

	sort.Strings(notGranted)
	return notGranted, nil
}

// queryPrivColumns 从 INFORMATION_SCHEMA 获取 mysql.user 表中所有 _priv 结尾的列，排除 Grant_priv。
func queryPrivColumns(ctx context.Context, conn *sqlx.Conn) ([]string, error) {
	query := "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS " +
		"WHERE TABLE_SCHEMA = 'mysql' AND TABLE_NAME = 'user' AND COLUMN_NAME LIKE '%\\_priv' " +
		"AND COLUMN_NAME != 'Grant_priv' ORDER BY ORDINAL_POSITION"

	var cols []string
	if err := sqlx.SelectContext(ctx, conn, &cols, query); err != nil {
		return nil, fmt.Errorf("query INFORMATION_SCHEMA.COLUMNS for _priv columns: %w", err)
	}
	if len(cols) == 0 {
		return nil, fmt.Errorf("no _priv columns found in mysql.user")
	}
	return cols, nil
}

// queryGrantPriv 查询 mysql.user 中指定用户的 Grant_priv 值。
func queryGrantPriv(ctx context.Context, conn *sqlx.Conn, user, host string) (string, error) {
	var val string
	query := "SELECT Grant_priv FROM mysql.user WHERE User = ? AND Host = ?"
	if err := conn.QueryRowxContext(ctx, query, user, host).Scan(&val); err != nil {
		return "", fmt.Errorf("query Grant_priv for %s@%s: %w", user, host, err)
	}
	return val, nil
}

// checkPrivSubset 检查 expected 是否是 actual 的子集。
// ALL PRIVILEGES 特判：
//   - actual 含 ALL PRIVILEGES -> 任何 expected 都算匹配
//   - expected 含 ALL PRIVILEGES -> actual 必须也含 ALL PRIVILEGES
//
// 返回缺失的权限列表。
func checkPrivSubset(expected, actual map[string]struct{}) []string {
	if _, ok := actual["ALL PRIVILEGES"]; ok {
		return nil
	}

	if _, ok := expected["ALL PRIVILEGES"]; ok {
		if _, ok2 := actual["ALL PRIVILEGES"]; !ok2 {
			return []string{"ALL PRIVILEGES"}
		}
		return nil
	}

	var missing []string
	for p := range expected {
		if _, ok := actual[p]; !ok {
			missing = append(missing, p)
		}
	}
	sort.Strings(missing)
	return missing
}

// parsePrivSet 将 "SELECT, INSERT, UPDATE" 解析为 {"SELECT", "INSERT", "UPDATE"}。
func parsePrivSet(privs string) []string {
	parts := strings.Split(privs, ",")
	result := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			result = append(result, strings.ToUpper(p))
		}
	}
	return result
}

// normalizeScope 去掉 scope 中的反引号。
// "`db`.*" -> "db.*"，"`db`.`table`" -> "db.table"
func normalizeScope(scope string) string {
	return strings.ReplaceAll(scope, "`", "")
}

// hasGrantOption 判断 rest 中是否含 GRANT OPTION。
func hasGrantOption(rest string) bool {
	return strings.Contains(strings.ToUpper(rest), "GRANT OPTION")
}

// formatPrivSet 将权限集合格式化为排序后的字符串，用于日志。
func formatPrivSet(privs map[string]struct{}) string {
	list := make([]string, 0, len(privs))
	for p := range privs {
		list = append(list, p)
	}
	sort.Strings(list)
	return strings.Join(list, ",")
}
