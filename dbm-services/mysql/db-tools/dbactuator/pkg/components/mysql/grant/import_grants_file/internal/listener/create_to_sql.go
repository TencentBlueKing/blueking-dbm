package listener

import (
	"fmt"
	"strings"
)

func (c *PrivListener) createToSql() string {
	sql := "CREATE USER IF NOT EXISTS"

	uao := strings.Join(
		func() []string {
			var uaos []string
			for _, ele := range c.AuthOptions {
				uaos = append(uaos, strings.TrimSpace(fmt.Sprintf("%s %s", ele.Username, ele.AuthClause)))
			}
			return uaos
		}(),
		", ",
	)
	sql = fmt.Sprintf("%s %s", sql, uao)

	if c.TlsNone != nil {
		sql += " REQUIRE NONE"
	} else {
		if c.TlsOptions != nil && len(c.TlsOptions) > 0 {
			sql = fmt.Sprintf("%s REQUIRE %s", sql, strings.Join(c.TlsOptions, " AND "))
		}
	}

	if c.ResourceOptions != nil && len(c.ResourceOptions) > 0 {
		sql = fmt.Sprintf("%s WITH %s", sql, strings.Join(c.ResourceOptions, " "))
	}

	if c.PasswordLockOption != "" {
		sql = fmt.Sprintf("%s %s", sql, c.PasswordLockOption)
	}
	return sql
}
