package listener

import (
	"slow-query-parser-service/pkg/parser"
)

func (r *SqlListener) EnterTableName(ctx *parser.TableNameContext) {
	r.Tables = append(r.Tables, ctx.GetText())
	if ctx.FullId().DOT_ID() != nil || ctx.FullId().DOT() != nil {
		dbContext := ctx.FullId().GetChild(0).(*parser.UidContext)
		r.Databases = append(r.Databases, dbContext.GetText())
	}
}
