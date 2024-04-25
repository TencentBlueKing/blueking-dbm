package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterDoStatement(ctx *parser.DoStatementContext) {
	r.Cmd = sqlcmd.CmdDmlDo
}
