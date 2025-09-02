package listener

import "dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"

func (c *PrivListener) EnterUserResourceOption(ctx *parsing.UserResourceOptionContext) {
	c.ResourceOptions = append(
		c.ResourceOptions,
		c.tokenStream.GetTextFromInterval(ctx.GetSourceInterval()),
	)
}
