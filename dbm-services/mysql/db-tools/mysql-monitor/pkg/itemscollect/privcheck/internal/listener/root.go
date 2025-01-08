package listener

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"
)

func (c *PrivListener) EnterRoot(ctx *parsing.RootContext) {
	raw := c.tokenStream.GetTextFromInterval(ctx.GetSourceInterval())

	if withGrantOptionPattern.MatchString(raw) {
		c.WithGrantOption = true
	}
	c.RawSQL = raw
}
