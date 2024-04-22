package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterCreateUserMysqlV56(ctx *parser.CreateUserMysqlV56Context) {
	r.Cmd = sqlcmd.CmdAdminCreateUser
}

func (r *SqlListener) EnterCreateUserMysqlV80(ctx *parser.CreateUserMysqlV80Context) {
	r.Cmd = sqlcmd.CmdAdminCreateUser
}
