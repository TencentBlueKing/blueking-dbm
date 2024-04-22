package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterGrantStatement(ctx *parser.GrantStatementContext) {
	r.Cmd = sqlcmd.CmdAdminGrant
}

func (r *SqlListener) EnterGrantProxy(ctx *parser.GrantProxyContext) {
	r.Cmd = sqlcmd.CmdAdminGrant
}
