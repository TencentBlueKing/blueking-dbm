package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterHandlerStatement(ctx *parser.HandlerStatementContext) {
	r.Cmd = sqlcmd.CmdDmlHandler
}
