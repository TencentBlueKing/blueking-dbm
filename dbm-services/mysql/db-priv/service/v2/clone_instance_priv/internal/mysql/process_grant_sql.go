package mysql

import (
	"fmt"
	"log/slog"
	"regexp"
	"strings"
)

var createUserPattern *regexp.Regexp
var grantPattern56 *regexp.Regexp

func init() {

	//CREATE USER  'kk'@'%' IDENTIFIED WITH 'mysql_native_password'
	//CREATE   USER   /*!50706  IF  NOT EXISTS */ 'kk'@'%' IDENTIFIED WITH
	//CREATE USER IF NOT EXISTS  'kk'@'%' IDENTIFIED WITH
	createUserPattern = regexp.MustCompile(`(?mi)^(create\s+user\s+(:?(:?/\*)?.*if\s+not\s+exists\s*(:?\*/)?)?)`)

	/*
		([][]string) (len=1 cap=10) {
		 ([]string) (len=5 cap=5) {
		  (string) (len=119) "GRANT USAGE ON *.* TO 'jeffrey'@'localhost' identified by '123' WITH grant option MAX_QUERIES_PER_HOUR 90 fake limit  ;",
		  (string) (len=19) "GRANT USAGE ON *.* ",
		  (string) (len=21) "'jeffrey'@'localhost'",
		  (string) (len=20) " identified by '123'",
		  (string) (len=56) " WITH grant option MAX_QUERIES_PER_HOUR 90 fake limit  ;"
		 }
		}
		([][]string) (len=1 cap=10) {
		 ([]string) (len=5 cap=5) {
		  (string) (len=106) "GRANT USAGE ON *.* TO 'jeffrey'@'localhost' identified by '123' WITH MAX_QUERIES_PER_HOUR 90 grant option;",
		  (string) (len=19) "GRANT USAGE ON *.* ",
		  (string) (len=21) "'jeffrey'@'localhost'",
		  (string) (len=20) " identified by '123'",
		  (string) (len=43) " WITH MAX_QUERIES_PER_HOUR 90 grant option;"
		 }
		}
		([][]string) (len=1 cap=10) {
		 ([]string) (len=5 cap=5) {
		  (string) (len=121) "GRANT USAGE ON *.* TO 'jeffrey'@'localhost' identified by '123' WITH grant option MAX_QUERIES_PER_HOUR 90 fake limit    ;",
		  (string) (len=19) "GRANT USAGE ON *.* ",
		  (string) (len=21) "'jeffrey'@'localhost'",
		  (string) (len=20) " identified by '123'",
		  (string) (len=58) " WITH grant option MAX_QUERIES_PER_HOUR 90 fake limit    ;"
		 }
		}
		([][]string) (len=1 cap=10) {
		 ([]string) (len=5 cap=5) {
		  (string) (len=43) "GRANT USAGE ON *.* TO 'jeffrey'@'localhost'",
		  (string) (len=19) "GRANT USAGE ON *.* ",
		  (string) (len=21) "'jeffrey'@'localhost'",
		  (string) "",
		  (string) ""
		 }
		}
		([][]string) <nil>


		这个正则会从 grant 语句中抓到 username, auth clause 和 with clause
		没怎么考虑非法的语句, 因为输入是从db上拿到的, 不太可能非法
		mysql逆天的允许 username 和 host 包含空格这样的东西, 所以这么写兼容比较好
	*/
	grantPattern56 = regexp.MustCompile(`(?miU)^(.*)to\s+(.*)(\s+identified.*)?(\s+with.*)?$`)
}

func ProcessGrantSql(privs []string, sourceAddr, targetAddr string, sourceVersion, targetVersion int, isStorage bool, logger *slog.Logger) (res []string, err error) {
	// spider 1 == 55
	// spider 3 == 57
	// 但是, spider 3 不能使用 /*!57xx / 这样的 version hint
	// 所以不能加 if not exists
	// 等到后面 spider 4 这里会贼麻烦
	logger.Info(fmt.Sprintf(
		"process grant sql, is storage: %t, source version: %d, target version: %d, privs count: %d",
		isStorage, sourceVersion, targetVersion, len(privs)),
	)
	if isStorage {
		if sourceVersion <= 56 && targetVersion >= 57 {
			c, g, err := trans56To57(privs, logger)
			if err != nil {
				return res, err
			}
			res = append(res, c...)
			res = append(res, g...)
		} else if sourceVersion >= 57 {
			res = addIfNotExists(privs)
		} else {
			res = privs
		}
	} else {
		res = privs
	}
	logger.Info(fmt.Sprintf("process grant sql, priv count after trans: %d", len(res)))
	res = replaceHost(res, sourceAddr, targetAddr)
	logger.Info(fmt.Sprintf("process grant sql, priv count after replace: %d", len(res)))

	return res, nil
}

func replaceHost(objs []string, sourceAddr, targetAddr string) (res []string) {
	sourceIp := strings.Split(sourceAddr, ":")[0]
	targetIp := strings.Split(targetAddr, ":")[0]
	for _, priv := range objs {
		res = append(
			res,
			strings.ReplaceAll(priv, sourceIp, targetIp),
		)
	}
	return res
}

func addIfNotExists(privs []string) (res []string) {
	for _, priv := range privs {
		res = append(
			res,
			createUserPattern.ReplaceAllString(strings.TrimSpace(priv), "CREATE USER /*!50706 IF NOT EXISTS */ "),
		)
	}
	return res
}

/*
GRANT

	priv_type [(column_list)]
	[, priv_type [(column_list)]] ...
	ON [object_type] priv_level
	TO user [auth_option] [, user [auth_option]] ...
	[REQUIRE {NONE | tls_option [[AND] tls_option] ...}]
	[WITH {GRANT OPTION | resource_option} ...]

5.6 的 grant 语句
grant xxx on  xx to username@userhost [identified xxx] [with xxx]
在更高版本的 mysql 中
1. with grant option 保留在 grant 语句中
2. 其他的 with 语句属于 resource_option, 用在 create user 中

To user ... [WITH] 之间的部分, 用在 create user 中
*/
func trans56To57(grantSqls56 []string, logger *slog.Logger) (createUserSqls []string, grantSqls []string, err error) {
	userIdentifiedByMap := make(map[string]string)
	userWithClauseMap := make(map[string]string)

	for _, orgSql := range grantSqls56 {
		// 先把语句清洗下, 这样正则能简单很多
		trimGrantSql := strings.Trim(orgSql, " ;")
		m := grantPattern56.FindAllStringSubmatch(trimGrantSql, -1)
		if m == nil {
			// 这里的概率非常非常低, 除非用错了
			err = fmt.Errorf("invalid grant sql: %s", trimGrantSql)
			logger.Error(
				fmt.Sprintf("trans grant 56 to 57, err: %s", err.Error()),
			)
			return nil, nil, err
		}

		userHost := strings.TrimSpace(m[0][2])         // 这个肯定有
		identifiedClause := strings.TrimSpace(m[0][3]) // 这个可能是空的

		// 用户对多个 db 授权时, 会输出多行 grant
		// 只有第一行有 identified clause
		// 所以用字典来存, 并且只有 clause 为空时才更新
		// 因为是从 db 中拿的, 不可能出现密码不一样的情况
		if _, ok := userIdentifiedByMap[userHost]; !ok {
			userIdentifiedByMap[userHost] = ""
		}
		if userIdentifiedByMap[userHost] == "" {
			userIdentifiedByMap[userHost] = generate56To57IdentifiedClause(identifiedClause)
		}

		withClause := strings.TrimSpace(m[0][4]) // 这个可能是空的
		// with grant option 归 grant 语句
		// 其他 with 选项归 create user
		withGrantOptionPart, withOtherPart := splitWithClause(withClause)
		if withGrantOptionPart != "" {
			withGrantOptionPart = "with " + withGrantOptionPart
		}

		// 拼一个新的 grant 语句
		// with grant option 留在这里
		grantSqls = append(
			grantSqls,
			fmt.Sprintf(
				`%s TO %s %s`,
				m[0][1],
				userHost,
				withGrantOptionPart,
			),
		)

		// 把其他的 with clause 存到另一个字典
		if _, ok := userWithClauseMap[userHost]; !ok {
			userWithClauseMap[userHost] = ""
		}
		userWithClauseMap[userHost] = withOtherPart
	}

	for userHost, identifiedClause := range userIdentifiedByMap {
		withOtherPart := userWithClauseMap[userHost]
		createUserSqls = append(
			createUserSqls,
			fmt.Sprintf(
				`CREATE USER /*!50706 IF NOT EXISTS */ %s %s %s`,
				userHost, identifiedClause, withOtherPart,
			),
		)
	}

	return createUserSqls, grantSqls, nil
}

/*
IDENTIFIED BY [PASSWORD] 'auth_string'
IDENTIFIED WITH auth_plugin
IDENTIFIED WITH auth_plugin AS 'auth_string'

目前看来, 只需要把包含 BY 的修改成
WITH 'mysql_native_password' AS
的形式
*/
func generate56To57IdentifiedClause(org string) string {
	orgUpper := strings.ToUpper(org)

	// 下面的 if 顺序不能变
	if strings.Contains(orgUpper, "BY PASSWORD") {
		// 新子串两头多加个空格当语法保护
		return strings.Replace(orgUpper, "BY PASSWORD", ` WITH 'mysql_native_password' AS `, -1)
	}

	if strings.Contains(orgUpper, "BY") {
		// 新子串两头多加个空格当语法保护
		return strings.Replace(orgUpper, "BY", ` WITH 'mysql_native_password' AS`, -1)
	}

	return org
}

func splitWithClause(org string) (grantOptionPart string, otherPart string) {
	// 清理下方便处理
	orgUpper := strings.Trim(strings.ToUpper(org), "WITH")
	// 因为是直接从 db 拿的, 所以根本不用考虑 grant option 中间有多个空格的情况
	if strings.Contains(orgUpper, "GRANT OPTION") {
		return "GRANT OPTION", strings.Replace(orgUpper, "GRANT OPTION", "", -1)
	}
	return "", orgUpper
}
