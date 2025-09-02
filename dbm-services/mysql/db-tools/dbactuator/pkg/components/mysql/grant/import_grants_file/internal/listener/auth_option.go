package listener

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
	"strings"

	"github.com/antlr4-go/antlr/v4"
)

func (c *PrivListener) ExitModuleAuthOption(ctx *parsing.ModuleAuthOptionContext) {
	c.fillAuthOption(ctx.UserName().GetSourceInterval(), ctx.GetSourceInterval())
}
func (c *PrivListener) ExitSimpleAuthOption(ctx *parsing.SimpleAuthOptionContext) {
	c.fillAuthOption(ctx.UserName().GetSourceInterval(), ctx.GetSourceInterval())
}
func (c *PrivListener) ExitStringAuthOption(ctx *parsing.StringAuthOptionContext) {
	c.fillAuthOption(ctx.UserName().GetSourceInterval(), ctx.GetSourceInterval())
}

func (c *PrivListener) ExitHashAuthOption(ctx *parsing.HashAuthOptionContext) {
	c.fillAuthOption(ctx.UserName().GetSourceInterval(), ctx.GetSourceInterval())
}

// normal grant 的 username 不要在  EnterUserName 去填充
func (c *PrivListener) fillAuthOption(userInterval antlr.Interval, optInterval antlr.Interval) {
	username := strings.TrimSpace(c.tokenStream.GetTextFromInterval(userInterval))
	clause := strings.TrimSpace(
		strings.Replace(c.tokenStream.GetTextFromInterval(optInterval), username, "", -1),
	)

	c.AuthOptions = append(
		c.AuthOptions,
		&AuthOptionStruct{Username: username, AuthClause: clause},
	)

	c.authOptionStrings = append(
		c.authOptionStrings,
		strings.TrimSpace(username+" "+clause),
	)
}
