package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterCallStatement(ctx *parser.CallStatementContext) {
	r.Cmd = sqlcmd.CmdDmlCall
	r.Functions = append(r.Functions, ctx.FullId().GetText())
}
