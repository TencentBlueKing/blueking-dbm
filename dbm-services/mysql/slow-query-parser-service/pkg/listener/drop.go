package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterDropDatabase(ctx *parser.DropDatabaseContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropEvent(ctx *parser.DropEventContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropIndex(ctx *parser.DropIndexContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropLogfileGroup(ctx *parser.DropLogfileGroupContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropProcedure(ctx *parser.DropProcedureContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropFunction(ctx *parser.DropFunctionContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropServer(ctx *parser.DropServerContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropTable(ctx *parser.DropTableContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropTablespace(ctx *parser.DropTablespaceContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropTrigger(ctx *parser.DropTriggerContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropView(ctx *parser.DropViewContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}

func (r *SqlListener) EnterDropRole(ctx *parser.DropRoleContext) {
	r.Cmd = sqlcmd.CmdDdlDrop
}
