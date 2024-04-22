package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterAlterUserMysqlV56(c *parser.AlterUserMysqlV56Context) {
	r.Cmd = sqlcmd.CmdAdminAlterUser
}

func (r *SqlListener) EnterAlterUserMysqlV80(ctx *parser.AlterUserMysqlV80Context) {
	r.Cmd = sqlcmd.CmdAdminAlterUser
}
