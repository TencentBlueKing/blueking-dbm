package checker

import (
	"context"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/reporter"

	"github.com/jmoiron/sqlx"
)

// Checker 检查器
type Checker struct {
	Config             *config.Config
	Mode               config.CheckMode
	db                 *sqlx.DB
	args               []string
	cancel             context.CancelFunc
	startTS            time.Time
	resultHistoryTable string
	resultDB           string
	resultTbl          string
	hasHistoryTable    bool
	reporter           *reporter.Reporter
}

// ChecksumSummary 结果汇总报表
type ChecksumSummary struct {
	Ts       time.Time `json:"ts"`
	Errors   int       `json:"errors"`
	Diffs    int       `json:"diffs"`
	Rows     int       `json:"rows"`
	DiffRows int       `json:"diff_rows"`
	Chunks   int       `json:"chunks"`
	Skipped  int       `json:"skipped"`
	Time     int       `json:"time"`
	Table    string    `json:"table"`
}

// PtExitFlag 退出位
type PtExitFlag struct {
	Flag     string `json:"flag"`
	Meaning  string `json:"meaning"`
	BitValue int    `json:"bit_value"`
}

// Output pt checksum输出
type Output struct {
	PtStderr    string            `json:"pt_stderr"`
	Summaries   []ChecksumSummary `json:"summaries"`
	PtExitFlags []PtExitFlag      `json:"pt_exit_flags"`
}
