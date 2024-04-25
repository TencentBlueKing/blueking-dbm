package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterInsertStatement(ctx *parser.InsertStatementContext) {
	r.Cmd = sqlcmd.CmdDmlInsert
}
