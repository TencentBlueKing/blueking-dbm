package listener

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"

	"strings"
)

func (c *PrivListener) EnterGrantStatement(ctx *parsing.GrantStatementContext) {
	c.IsGrantPriv = true
	spl := strings.Split(ctx.PrivilegeLevel().GetText(), ".")
	c.DBName = strings.Trim(spl[0], "'`")
	c.TableName = strings.Trim(spl[1], "'`")
}
