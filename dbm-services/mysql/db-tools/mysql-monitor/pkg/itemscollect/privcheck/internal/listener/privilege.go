package listener

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"
)

func (c *PrivListener) EnterPrivilege(ctx *parsing.PrivilegeContext) {
	c.Privileges = append(
		c.Privileges,
		c.tokenStream.GetTextFromInterval(ctx.GetSourceInterval()),
	)
}
