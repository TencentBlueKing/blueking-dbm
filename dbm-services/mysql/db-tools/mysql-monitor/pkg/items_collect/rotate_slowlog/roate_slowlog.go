package rotate_slowlog

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
)

var name = "rotate-slowlog"

// Dummy TODO
type Dummy struct {
	db *sqlx.DB
}

/*
perl 版本中执行了一系列的操作
   my @sqls = (
     qq{select \@\@global.slow_query_log into \@sq_log_save},
     qq{set global slow_query_log=off},
     qq{select sleep(2)},
     qq{FLUSH SLOW LOGS},
     qq{select sleep(3)},
     qq{set global slow_query_log=\@sq_log_save},
   );

但是似乎只需要 FLUSH SLOW LOGS
*/

// Run TODO
func (d *Dummy) Run() (msg string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var slowLogPath string
	var slowLogOn bool
	err = d.db.QueryRowxContext(
		ctx,
		`SELECT @@slow_query_log, @@slow_query_log_file`,
	).Scan(&slowLogOn, &slowLogPath)
	if err != nil {
		slog.Error("query slow_query_log, slow_query_log_file", err)
		return "", err
	}
	slog.Info(
		"rotate slow log",
		slog.Bool("slow_query_log", slowLogOn),
		slog.String("slow_query_log_file", slowLogPath),
	)

	if !slowLogOn {
		return "", nil
	}

	slowLogDir := filepath.Dir(slowLogPath)
	slowLogFile := filepath.Base(slowLogPath)

	historySlowLogFilePath := filepath.Join(
		slowLogDir,
		fmt.Sprintf("%s.%d", slowLogFile, time.Now().Weekday()),
	)

	/*
		1. 文件不存在, st == nil, err != nil && os.IsNotExist(err) == true
		2. 文件存在, st != nil, err == nil
	*/
	st, err := os.Stat(historySlowLogFilePath)
	if err != nil {
		if !os.IsNotExist(err) { // 文件存在
			slog.Error("get history slow log file stat", err, slog.String("history file path", historySlowLogFilePath))
			return "", nil
		}
		// 文件不存在
	} else {
		// 3 天只是为了方便, 实际控制的是 1 周 rotate 1 次
		// 短时间连续执行不会重复 rotate
		if time.Now().Sub(st.ModTime()) < 3*24*time.Hour {
			slog.Info(
				"rotate slow log skip too frequency call",
				slog.Time("now", time.Now()),
				slog.Time("history file mod time", st.ModTime()),
				slog.String("history file", historySlowLogFilePath),
			)
			return "", nil
		}
	}

	mvCmd := exec.Command(
		"mv",
		slowLogPath,
		historySlowLogFilePath,
	)

	var stderr bytes.Buffer
	mvCmd.Stderr = &stderr
	err = mvCmd.Run()
	if err != nil {
		slog.Error("mv slow log", err, slog.String("stderr", stderr.String()))
		return "", err
	}

	touchCmd := exec.Command("touch", slowLogPath)
	stderr.Reset()
	touchCmd.Stderr = &stderr
	err = touchCmd.Run()
	if err != nil {
		slog.Error("touch slow log", err, slog.String("stderr", stderr.String()))
		return "", err
	}

	_, err = d.db.ExecContext(ctx, `FLUSH SLOW LOGS`)
	if err != nil {
		slog.Error("flush slow logs", err)
		return "", err
	}

	return "", nil
}

// Name TODO
func (d *Dummy) Name() string {
	return name
}

// NewRotateSlowLog TODO
func NewRotateSlowLog(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Dummy{db: cc.MySqlDB}
}

// RegisterRotateSlowLog TODO
func RegisterRotateSlowLog() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return name, NewRotateSlowLog
}
