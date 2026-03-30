package pkg

import "regexp"

// QuoteStyle 表示 SQL 语句中用户名/主机名的引号风格。
type QuoteStyle int

const (
	// QuoteSingle 单引号风格：'user'@'host'（MySQL 5.5/5.6/5.7）
	QuoteSingle QuoteStyle = iota
	// QuoteBacktick 反引号风格：`user`@`host`（MySQL 8.0 / Spider4）
	QuoteBacktick
)

// QuoteUser 根据引号风格格式化 'user'@'host' 或 `user`@`host`。
func QuoteUser(user, host string, style QuoteStyle) string {
	if style == QuoteBacktick {
		return "`" + user + "`@`" + host + "`"
	}
	return "'" + user + "'@'" + host + "'"
}

// userHostPattern 是匹配 'user'@'host' 或 `user`@`host` 的正则片段。
// 产生 2 个捕获组：(user, host)，其中单引号和反引号各占一对。
// 总共 4 个捕获组：(sq_user, sq_host, bq_user, bq_host)
const userHostPattern = `(?:'([^']+)'@'([^']+)'|` + "`([^`]+)`@`([^`]+)`)"

// identifiedWithPattern 匹配 IDENTIFIED WITH 'plugin' [AS 'hash']
// plugin 和 hash 始终使用单引号（即使 user@host 用反引号）
const identifiedWithPattern = `\s+IDENTIFIED\s+WITH\s+'([^']+)'(?:\s+AS\s+'([^']*)')?`

// identifiedByPasswordPattern 匹配 IDENTIFIED BY PASSWORD '*hash'
// hash 始终使用单引号
const identifiedByPasswordPattern = `\s+IDENTIFIED\s+BY\s+PASSWORD\s+'([^']+)'`

var (
	// ReCreateUser 匹配 5.7/8.0 的 CREATE USER 语句。
	// 示例: CREATE USER 'app'@'%' IDENTIFIED WITH 'mysql_native_password' AS '*2470C...' REQUIRE NONE ...
	// 示例: CREATE USER IF NOT EXISTS `app`@`%` IDENTIFIED WITH 'mysql_native_password' AS '*2470C...'
	// 捕获组: (sq_user, sq_host, bq_user, bq_host, plugin, hash, rest)
	ReCreateUser *regexp.Regexp

	// ReGrantWithAuth 匹配 5.5/5.6 带 IDENTIFIED BY PASSWORD 的 GRANT 语句。
	// 示例: GRANT SELECT ON `db`.* TO 'app'@'%' IDENTIFIED BY PASSWORD '*2470C...'
	// 捕获组: (privs, scope, sq_user, sq_host, bq_user, bq_host, hash, rest)
	ReGrantWithAuth *regexp.Regexp

	// ReGrantPlain 匹配不含认证信息的纯 GRANT 语句。
	// 示例: GRANT SELECT ON `db`.* TO 'app'@'%'
	// 示例: GRANT SELECT ON `db`.* TO `app`@`%` WITH GRANT OPTION
	// 捕获组: (privs, scope, sq_user, sq_host, bq_user, bq_host, rest)
	ReGrantPlain *regexp.Regexp

	// ReUserHost 从 GRANT 语句中提取 user@host 部分。
	// 捕获组: (sq_user, sq_host, bq_user, bq_host)
	ReUserHost *regexp.Regexp

	// ReCreateUserLegacy 匹配 5.5/5.6/Spider3 的 CREATE USER 语句（IDENTIFIED BY PASSWORD 格式）。
	// 示例: CREATE USER IF NOT EXISTS 'app'@'%' IDENTIFIED BY PASSWORD '*2470C...'
	// 捕获组: (sq_user, sq_host, bq_user, bq_host, hash, rest)
	ReCreateUserLegacy *regexp.Regexp

	// ReCreateUserPlain 匹配不含 IDENTIFIED 子句的 CREATE USER 语句（无密码用户）。
	// 示例: CREATE USER 'app'@'%'
	// 示例: CREATE USER /*!50706 IF NOT EXISTS */ 'app'@'%'
	// 捕获组: (sq_user, sq_host, bq_user, bq_host, rest)
	ReCreateUserPlain *regexp.Regexp

	// ReCreateUserPrefix 匹配 CREATE USER 语句开头，用于插入 IF NOT EXISTS。
	// 兼容已有 IF NOT EXISTS 和 /*!50706 IF NOT EXISTS */ 的情况。
	ReCreateUserPrefix *regexp.Regexp
)

func init() {
	// CREATE USER [IF NOT EXISTS] 'user'@'host' IDENTIFIED WITH 'plugin' [AS 'hash'] [rest...]
	// 兼容 /*!50706 IF NOT EXISTS */ 和原生 IF NOT EXISTS
	// 注意：AS 'hash' 部分是可选的，空密码用户没有该子句
	ReCreateUser = regexp.MustCompile(
		`(?i)^\s*CREATE\s+USER\s+(?:(?:/\*!?\d*\s*)?IF\s+NOT\s+EXISTS\s*(?:\*/)?\s*)?` +
			userHostPattern + identifiedWithPattern + `(.*)$`,
	)

	// GRANT ... ON ... TO 'user'@'host' IDENTIFIED BY PASSWORD '*hash' [rest...]
	ReGrantWithAuth = regexp.MustCompile(
		`(?i)^\s*GRANT\s+(.+?)\s+ON\s+(\S+)\s+TO\s+` +
			userHostPattern + identifiedByPasswordPattern + `(.*)$`,
	)

	// GRANT ... ON ... TO 'user'@'host' [rest...]
	ReGrantPlain = regexp.MustCompile(
		`(?i)^\s*GRANT\s+(.+?)\s+ON\s+(\S+)\s+TO\s+` + userHostPattern + `(.*)$`,
	)

	// TO 'user'@'host' 或 TO `user`@`host` — 从任意 GRANT 行中提取 user 和 host
	ReUserHost = regexp.MustCompile(`TO\s+` + userHostPattern)

	// CREATE USER [IF NOT EXISTS] 'user'@'host' IDENTIFIED BY PASSWORD '*hash'
	// 匹配 5.5/5.6/Spider3 的 legacy 格式 CREATE USER
	ReCreateUserLegacy = regexp.MustCompile(
		`(?i)^\s*CREATE\s+USER\s+(?:(?:/\*!?\d*\s*)?IF\s+NOT\s+EXISTS\s*(?:\*/)?\s*)?` +
			userHostPattern + identifiedByPasswordPattern + `(.*)$`,
	)

	// CREATE USER [IF NOT EXISTS] 'user'@'host' [rest...]
	// 无 IDENTIFIED 子句，匹配无密码用户
	ReCreateUserPlain = regexp.MustCompile(
		`(?i)^\s*CREATE\s+USER\s+(?:(?:/\*!?\d*\s*)?IF\s+NOT\s+EXISTS\s*(?:\*/)?\s*)?` +
			userHostPattern + `(.*)$`,
	)

	// CREATE USER [/*!50706 IF NOT EXISTS */] 'user'@'host' ...
	// 匹配 CREATE USER 开头部分，用于在没有 IF NOT EXISTS 时插入
	ReCreateUserPrefix = regexp.MustCompile(
		`(?i)^\s*CREATE\s+USER\s+`,
	)
}

// ExtractUserHost 从 userHostPattern 的 4 个捕获组中提取 user、host 和引号风格。
// offset 是 userHostPattern 在整个正则中的第一个捕获组的索引（从 1 开始）。
// 例如 ReGrantPlain 中 userHostPattern 从第 3 个捕获组开始，offset=3。
func ExtractUserHost(matches []string, offset int) (user, host string, style QuoteStyle) {
	if matches[offset] != "" {
		return matches[offset], matches[offset+1], QuoteSingle
	}
	return matches[offset+2], matches[offset+3], QuoteBacktick
}

// ExtractCreateUserFields 从 ReCreateUser 的匹配结果中提取所有字段。
// 返回: user, host, plugin, hash, rest, quoteStyle
func ExtractCreateUserFields(matches []string) (user, host, plugin, hash, rest string, style QuoteStyle) {
	user, host, style = ExtractUserHost(matches, 1)
	plugin = matches[5]
	hash = matches[6]
	rest = matches[7]
	return
}

// ExtractGrantWithAuthFields 从 ReGrantWithAuth 的匹配结果中提取所有字段。
// 返回: privs, scope, user, host, hash, rest, quoteStyle
func ExtractGrantWithAuthFields(matches []string) (privs, scope, user, host, hash, rest string, style QuoteStyle) {
	privs = matches[1]
	scope = matches[2]
	user, host, style = ExtractUserHost(matches, 3)
	hash = matches[7]
	rest = matches[8]
	return
}

// ExtractGrantPlainFields 从 ReGrantPlain 的匹配结果中提取所有字段。
// 返回: privs, scope, user, host, rest, quoteStyle
func ExtractGrantPlainFields(matches []string) (privs, scope, user, host, rest string, style QuoteStyle) {
	privs = matches[1]
	scope = matches[2]
	user, host, style = ExtractUserHost(matches, 3)
	rest = matches[7]
	return
}

// ExtractUserHostFields 从 ReUserHost 的匹配结果中提取 user 和 host。
// 返回: user, host, quoteStyle
func ExtractUserHostFields(matches []string) (user, host string, style QuoteStyle) {
	return ExtractUserHost(matches, 1)
}

// ExtractCreateUserLegacyFields 从 ReCreateUserLegacy 的匹配结果中提取所有字段。
// 返回: user, host, hash, rest, quoteStyle
func ExtractCreateUserLegacyFields(matches []string) (user, host, hash, rest string, style QuoteStyle) {
	user, host, style = ExtractUserHost(matches, 1)
	hash = matches[5]
	rest = matches[6]
	return
}

// ExtractCreateUserPlainFields 从 ReCreateUserPlain 的匹配结果中提取所有字段。
// 返回: user, host, rest, quoteStyle
func ExtractCreateUserPlainFields(matches []string) (user, host, rest string, style QuoteStyle) {
	user, host, style = ExtractUserHost(matches, 1)
	rest = matches[5]
	return
}
