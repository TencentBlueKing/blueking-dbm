package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterSimpleSelect(ctx *parser.SimpleSelectContext) {
	r.Cmd = sqlcmd.CmdDmlSelect
}

func (r *SqlListener) EnterParenthesisSelect(ctx *parser.ParenthesisSelectContext) {
	r.Cmd = sqlcmd.CmdDmlSelect
}

func (r *SqlListener) EnterUnionSelect(ctx *parser.UnionSelectContext) {
	r.Cmd = sqlcmd.CmdDmlSelect
}

func (r *SqlListener) EnterUnionParenthesisSelect(ctx *parser.UnionParenthesisSelectContext) {
	r.Cmd = sqlcmd.CmdDmlSelect
}

func (r *SqlListener) EnterWithLateralStatement(ctx *parser.WithLateralStatementContext) {
	r.Cmd = sqlcmd.CmdDmlSelect
}
