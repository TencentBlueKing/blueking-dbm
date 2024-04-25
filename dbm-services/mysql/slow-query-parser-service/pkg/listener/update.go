package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterUpdateStatement(ctx *parser.UpdateStatementContext) {
	r.Cmd = sqlcmd.CmdDmlUpdate
}
