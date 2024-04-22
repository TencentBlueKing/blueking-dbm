package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterSetRole(ctx *parser.SetRoleContext) {
	r.Cmd = sqlcmd.CmdDdlSetRole
}
