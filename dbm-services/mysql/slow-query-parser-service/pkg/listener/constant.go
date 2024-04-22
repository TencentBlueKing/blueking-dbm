package listener

import "slow-query-parser-service/pkg/parser"

func (r *SqlListener) EnterConstant(ctx *parser.ConstantContext) {
	if ctx.StringLiteral() != nil || ctx.BIT_STRING() != nil {
		r.rewriter.ReplaceDefault(ctx.GetSourceInterval().Start, ctx.GetSourceInterval().Stop, `'?'`)
	} else {
		r.rewriter.ReplaceDefault(ctx.GetSourceInterval().Start, ctx.GetSourceInterval().Stop, `?`)
	}
}
