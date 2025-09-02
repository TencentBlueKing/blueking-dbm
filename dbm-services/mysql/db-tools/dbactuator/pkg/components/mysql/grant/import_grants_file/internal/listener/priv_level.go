package listener

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
	"strings"
)

// 不会出现
//func (c *PrivListener) EnterCurrentSchemaPriviLevel(ctx *parsing.CurrentSchemaPriviLevelContext) {
//
//}

func (c *PrivListener) EnterGlobalPrivLevel(ctx *parsing.GlobalPrivLevelContext) {
	c.DBName = "*"
	c.TableName = "*"
}

func (c *PrivListener) EnterDefiniteSchemaPrivLevel(ctx *parsing.DefiniteSchemaPrivLevelContext) {
	c.DBName = strings.Trim(ctx.Uid().GetText(), "'`")
	c.TableName = "*"
}
func (c *PrivListener) EnterDefiniteFullTablePrivLevel(ctx *parsing.DefiniteFullTablePrivLevelContext) {
	c.DBName = strings.Trim(ctx.Uid(0).GetText(), "'`")
	c.TableName = strings.Trim(ctx.Uid(1).GetText(), "'`")
}

// EnterDefiniteFullTablePrivLevel2
// 不知道这是个啥
func (c *PrivListener) EnterDefiniteFullTablePrivLevel2(ctx *parsing.DefiniteFullTablePrivLevel2Context) {
	c.DBName = strings.Trim(ctx.Uid().GetText(), "'`")
	c.TableName = strings.Trim(ctx.DottedId().Uid().GetText(), "'`")

}

// 不会出现
//func (c *PrivListener) EnterDefiniteTablePrivLevel(ctx *parsing.DefiniteTablePrivLevelContext) {
//
//}
