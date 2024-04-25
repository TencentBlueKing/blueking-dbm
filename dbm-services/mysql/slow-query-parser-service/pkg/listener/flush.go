package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterFlushStatement(c *parser.FlushStatementContext) {
	r.Cmd = sqlcmd.CmdAdminFlush
}
