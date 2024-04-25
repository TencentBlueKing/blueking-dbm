package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterTruncateTable(ctx *parser.TruncateTableContext) {
	r.Cmd = sqlcmd.CmdDdlTruncateTable
}
