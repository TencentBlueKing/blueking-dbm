package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterLoadDataStatement(ctx *parser.LoadDataStatementContext) {
	r.Cmd = sqlcmd.CmdDmlLoad
}

func (r *SqlListener) EnterLoadXmlStatement(ctx *parser.LoadXmlStatementContext) {
	r.Cmd = sqlcmd.CmdDmlLoad
}
