package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterRenameTable(ctx *parser.RenameTableContext) {
	r.Cmd = sqlcmd.CmdDdlRenameTable
}
