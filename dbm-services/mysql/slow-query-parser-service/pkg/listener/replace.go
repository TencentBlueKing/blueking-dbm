package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterReplaceStatement(ctx *parser.ReplaceStatementContext) {
	r.Cmd = sqlcmd.CmdDmlReplace
}
