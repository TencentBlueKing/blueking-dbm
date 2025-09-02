package listener

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
)

func (c *PrivListener) EnterRoot(ctx *parsing.RootContext) {
	c.RawSQL = c.tokenStream.GetTextFromInterval(ctx.GetSourceInterval())
}
