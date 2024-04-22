package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterDetailRevoke(ctx *parser.DetailRevokeContext) {
	r.Cmd = sqlcmd.CmdAdminRevoke
}

func (r *SqlListener) EnterShortRevoke(ctx *parser.ShortRevokeContext) {
	r.Cmd = sqlcmd.CmdAdminRevoke
}

func (r *SqlListener) EnterRoleRevoke(ctx *parser.RoleRevokeContext) {
	r.Cmd = sqlcmd.CmdAdminRevoke
}

func (r *SqlListener) EnterRevokeProxy(ctx *parser.RevokeProxyContext) {
	r.Cmd = sqlcmd.CmdAdminRevoke
}
