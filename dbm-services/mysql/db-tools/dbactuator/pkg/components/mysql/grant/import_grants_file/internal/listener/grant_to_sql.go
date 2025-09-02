package listener

import (
	"fmt"
	"strings"
)

func (c *PrivListener) grantToSql() string {
	switch c.GrantType {
	case GrantStatementTypeNormal:
		return c.normalGrantToSql()
	case GrantStatementTypeRole:
		return c.roleGrantToSql()
	default:
		return c.proxyGrantToSql()
	}
}

func (c *PrivListener) normalGrantToSql() string {
	sql := "GRANT " + c.Privileges + " ON"
	if c.PrivObject != "" {
		sql += " " + c.PrivObject
	}
	sql += fmt.Sprintf(" %s.%s TO ",
		func() string {
			if c.DBName == "*" || c.DBName == "%" {
				return "*"
			} else {
				return fmt.Sprintf("`%s`", c.DBName)
			}
		}(),
		func() string {
			if c.TableName == "*" || c.TableName == "%" {
				return "*"
			} else {
				return fmt.Sprintf("`%s`", c.TableName)
			}
		}(),
	)

	sql += strings.Join(func() (res []string) {
		for _, ele := range c.AuthOptions {
			res = append(
				res, strings.TrimSpace(fmt.Sprintf("%s %s", ele.Username, ele.AuthClause)))
		}
		return res
	}(), ", ")

	if c.TlsNone != nil {
		sql += " REQUIRE NONE"
	} else {
		if c.TlsOptions != nil && len(c.TlsOptions) > 0 {
			sql += " REQUIRE " + strings.Join(c.TlsOptions, " AND ")
		}
	}

	var opts string
	if c.WithGrantOption {
		opts = "GRANT OPTION"
	}
	if c.ResourceOptions != nil && len(c.ResourceOptions) > 0 {
		opts += " " + strings.Join(c.ResourceOptions, " ")
	}
	opts = strings.TrimSpace(opts)
	if opts != "" {
		sql += " WITH " + opts
	}

	if c.RoleOption != "" {
		sql += " " + c.RoleOption
	}

	return sql
}

func (c *PrivListener) roleGrantToSql() string {
	sql := "GRANT " + strings.Join(c.FromUserOrIds, ", ") + " TO " + strings.Join(c.ToUserOrIds, ", ")
	if c.WithAdminOption {
		sql += " WITH ADMIN OPTION"
	}
	return sql
}

func (c *PrivListener) proxyGrantToSql() string {
	sql := "GRANT PROXY ON " + c.FromUsername + " TO " + strings.Join(c.ToUsernames, ", ")
	if c.WithGrantOption {
		sql += " WITH GRANT OPTION"
	}
	return sql
}
