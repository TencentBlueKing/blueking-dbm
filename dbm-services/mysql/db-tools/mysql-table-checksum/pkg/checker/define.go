package checker

import (
	"bytes"
	"compress/gzip"
	"context"
	"encoding/base64"
	"encoding/json"
	"log/slog"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/jmoiron/sqlx"
)

// Checker 检查器
type Checker struct {
	Config             *config.Config
	Mode               config.CheckMode
	db                 *sqlx.DB
	conn               *sqlx.Conn
	args               []string
	cancel             context.CancelFunc
	startTS            time.Time
	resultHistoryTable string
	resultDB           string
	resultTbl          string
	hasHistoryTable    bool
	//reporter           *reporter.Reporter
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

func (c *Output) String() string {
	b, _ := json.Marshal(*c)
	return string(b)
}

func (c *Output) ZipString() (string, error) {
	b, _ := json.Marshal(*c)
	slog.Info("run checksum", slog.String("raw report", string(b)))

	var zb bytes.Buffer
	gz, err := gzip.NewWriterLevel(&zb, gzip.BestCompression)
	if err != nil {
		return "", err
	}
	defer func() {
		_ = gz.Close()
	}()

	_, err = gz.Write(b)
	if err != nil {
		return "", err
	}

	err = gz.Flush()
	if err != nil {
		return "", err
	}

	err = gz.Close()
	if err != nil {
		return "", err
	}

	slog.Info("run checksum", slog.Any("zipped report", zb.Bytes()))

	encodeReport := base64.StdEncoding.EncodeToString(zb.Bytes())
	slog.Info("run checksum", slog.String("encoded report", encodeReport))
	return encodeReport, nil
}
