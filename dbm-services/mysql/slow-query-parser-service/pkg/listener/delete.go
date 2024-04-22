package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterDeleteStatement(ctx *parser.DeleteStatementContext) {
	r.Cmd = sqlcmd.CmdDmlDelete
}
