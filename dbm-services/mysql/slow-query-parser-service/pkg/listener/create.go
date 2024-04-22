package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterCreateDatabase(ctx *parser.CreateDatabaseContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateEvent(ctx *parser.CreateEventContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateIndex(ctx *parser.CreateIndexContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateLogfileGroup(ctx *parser.CreateLogfileGroupContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateProcedure(ctx *parser.CreateProcedureContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateFunction(ctx *parser.CreateFunctionContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateServer(ctx *parser.CreateServerContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCopyCreateTable(ctx *parser.CopyCreateTableContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterQueryCreateTable(ctx *parser.QueryCreateTableContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterColumnCreateTable(ctx *parser.ColumnCreateTableContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateTablespaceInnodb(ctx *parser.CreateTablespaceInnodbContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateTablespaceNdb(ctx *parser.CreateTablespaceNdbContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateTrigger(ctx *parser.CreateTriggerContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateView(ctx *parser.CreateViewContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}

func (r *SqlListener) EnterCreateRole(ctx *parser.CreateRoleContext) {
	r.Cmd = sqlcmd.CmdDdlCreate
}
