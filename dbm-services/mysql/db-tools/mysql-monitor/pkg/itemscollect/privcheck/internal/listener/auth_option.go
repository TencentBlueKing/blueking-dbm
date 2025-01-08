package listener

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"
	"strings"
)

func (c *PrivListener) EnterModuleAuthOption(ctx *parsing.ModuleAuthOptionContext) {
	c.fillUserHost(ctx.UserName().GetText())
}
func (c *PrivListener) EnterSimpleAuthOption(ctx *parsing.SimpleAuthOptionContext) {
	c.fillUserHost(ctx.UserName().GetText())
}
func (c *PrivListener) EnterStringAuthOption(ctx *parsing.StringAuthOptionContext) {
	c.fillUserHost(ctx.UserName().GetText())
}

func (c *PrivListener) EnterHashAuthOption(ctx *parsing.HashAuthOptionContext) {
	c.fillUserHost(ctx.UserName().GetText())
	c.Password = strings.Trim(ctx.GetHashed().GetText(), "'")
}

func (c *PrivListener) fillUserHost(username string) {
	c.RawUsername = username
	spu := strings.Split(username, "@")
	c.Username = strings.Trim(spu[0], "'`")
	c.Host = strings.Trim(spu[1], "`'")
}
