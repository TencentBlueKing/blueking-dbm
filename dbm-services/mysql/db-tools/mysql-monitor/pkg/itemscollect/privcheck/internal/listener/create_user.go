package listener

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"
)

func (c *PrivListener) EnterCreateUserMysqlV56(ctx *parsing.CreateUserMysqlV56Context) {
	c.IsCreateUser = true
}

func (c *PrivListener) EnterCreateUserMysqlV80(ctx *parsing.CreateUserMysqlV80Context) {
	c.IsCreateUser = true
}
