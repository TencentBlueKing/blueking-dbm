package listener

import (
	"slow-query-parser-service/pkg/parser"
	"slow-query-parser-service/pkg/sqlcmd"
)

func (r *SqlListener) EnterAnalyzeTable(ctx *parser.AnalyzeTableContext) {
	r.Cmd = sqlcmd.CmdAdminAnalyze
}

func (r *SqlListener) EnterCheckTable(ctx *parser.CheckTableContext) {
	r.Cmd = sqlcmd.CmdAdminCheckTable
}

func (r *SqlListener) EnterChecksumTable(ctx *parser.ChecksumTableContext) {
	r.Cmd = sqlcmd.CmdAdminChecksumTable
}

func (r *SqlListener) EnterOptimizeTable(ctx *parser.OptimizeTableContext) {
	r.Cmd = sqlcmd.CmdAdminOptimizeTable
}

func (r *SqlListener) EnterRepairTable(ctx *parser.RepairTableContext) {
	r.Cmd = sqlcmd.CmdAdminRepair
}
