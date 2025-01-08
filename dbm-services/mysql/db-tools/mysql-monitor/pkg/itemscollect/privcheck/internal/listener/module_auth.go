package listener

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"

	"strings"
)

func (c *PrivListener) EnterModule(ctx *parsing.ModuleContext) {
	if ctx.STRING_LITERAL() != nil {
		c.Password = strings.Trim(ctx.STRING_LITERAL().GetText(), "'")
	} else {
		c.Password = ""
	}
}
