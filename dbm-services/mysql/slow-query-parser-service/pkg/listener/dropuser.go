package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterDropUser(ctx *parser.DropUserContext) {
	r.Cmd = sqlcmd.CmdAdminDropUser
}
