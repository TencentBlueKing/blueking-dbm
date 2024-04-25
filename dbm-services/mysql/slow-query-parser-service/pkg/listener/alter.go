package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterAlterSimpleDatabase(ctx *parser.AlterSimpleDatabaseContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterUpgradeName(ctx *parser.AlterUpgradeNameContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterEvent(ctx *parser.AlterEventContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterFunction(ctx *parser.AlterFunctionContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterInstance(ctx *parser.AlterInstanceContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterLogfileGroup(ctx *parser.AlterLogfileGroupContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterProcedure(ctx *parser.AlterProcedureContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterServer(ctx *parser.AlterServerContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterTable(ctx *parser.AlterTableContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterTablespace(ctx *parser.AlterTablespaceContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}

func (r *SqlListener) EnterAlterView(ctx *parser.AlterViewContext) {
	r.Cmd = sqlcmd.CmdDdlAlter
}
