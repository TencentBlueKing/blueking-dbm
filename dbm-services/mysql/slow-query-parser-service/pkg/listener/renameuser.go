package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterRenameUser(ctx *parser.RenameUserContext) {
	r.Cmd = sqlcmd.CmdAdminRenameUser
}
