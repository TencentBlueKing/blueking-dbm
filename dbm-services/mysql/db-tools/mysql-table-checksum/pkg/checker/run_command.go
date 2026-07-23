package checker

import (
	"bytes"
	"context"

	"errors"
	"fmt"
	"log/slog"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/avast/retry-go/v5"
)

var roundStartStr = "_dba_fake_round_start"
var dailyStr = "_dba_fake_daily"

// var demandStartStr = "_dba_fake_demand_start"
var demandEndStr = "_dba_fake_demand_end"

// EmptySummaryError 表示校验摘要为空的错误，用于 RetryIf 判断是否需要重试
// 当 pt-table-checksum 执行完成但没有返回校验摘要时，返回此错误触发重试
type EmptySummaryError struct {
	Message string
}

func (e *EmptySummaryError) Error() string {
	if e.Message == "" {
		return "checksum summary is empty, need retry"
	}
	return e.Message
}

// IsEmptySummaryError 判断错误是否为 EmptySummaryError 类型
func IsEmptySummaryError(err error) bool {
	var emptySummaryErr *EmptySummaryError
	return errors.As(err, &emptySummaryErr)
}

func (r *Checker) Run() error {
	slog.Info("run mode", slog.String("mode", string(r.Mode)))
	switch r.Mode {
	case config.GeneralMode:
		err := r.preRunGeneral()
		if err != nil {
			slog.Error("run checksum", slog.String("error", err.Error()))
			return err
		}

		if !config.ChecksumConfig.Enable {
			slog.Info("run checksum disabled")
			return nil
		}

		err = r.runGeneral()
		if err != nil {
			slog.Error("run checksum", slog.String("error", err.Error()))
			return err
		}
		err = r.moveResult()
		if err != nil {
			slog.Error("run checksum", slog.String("error", err.Error()))
			return err
		}
		return nil
	case config.DemandMode, config.DtsMode:
		err := r.runDemand()
		if err != nil {
			return err
		}

		err = r.postRunDemand(true)
		if err != nil {
			return err
		}

		return nil
	default:
		err := fmt.Errorf("run mode %s not supported", r.Mode)
		slog.Error("run checksum", slog.String("error", err.Error()))
		return err
	}
}

func (r *Checker) postRunDemand(demand bool) error {
	err := r.writeFakeResult(demandEndStr, demandEndStr, demand)
	if err != nil {
		slog.Error("run demand checksum", slog.String("error", err.Error()))
		return err
	}
	return nil
}

func (r *Checker) preRunGeneral() error {
	err := r.writeFakeResult(dailyStr, dailyStr, false)
	if err != nil {
		slog.Error("run checksum", slog.String("error", err.Error()))
		return err
	}
	if !config.ChecksumConfig.Enable {
		slog.Info("run checksum disabled")
		return nil
	}
	_, err = r.conn.ExecContext(
		context.Background(),
		fmt.Sprintf("DELETE FROM `%s`.`%s` WHERE ts < NOW() - INTERVAL 10 DAY", r.resultDB, r.resultHistoryTable),
	)
	if err != nil {
		slog.Error("run checksum", slog.String("error", err.Error()))
	}
	return nil
}

func (r *Checker) runGeneral() error {
	var cleanUpErr error
	var retryTime uint = 2

	err := retry.New(
		retry.Attempts(retryTime),
		retry.Delay(2*time.Second),
		retry.RetryIf(
			func(err error) bool {
				// 只有当错误是 EmptySummaryError 时才重试
				isEmptySummary := IsEmptySummaryError(err)
				shouldRetry := isEmptySummary && cleanUpErr == nil
				slog.Info(
					"RetryIf check",
					slog.Bool("isEmptySummaryError", isEmptySummary),
					slog.Any("cleanUpErr", cleanUpErr),
					slog.Bool("shouldRetry", shouldRetry),
					slog.Any("originalErr", err),
				)
				return shouldRetry
			},
		),
		retry.OnRetry(
			func(n uint, e error) {
				slog.Info("retry run checksum", slog.Int("retry", int(n)), slog.Any("error", e))

				/*
					replace into infodba_schema.checksum
					values('0.0.0.0','3306', 'test', 'test', 0, NULL, NULL, '1=1', '1=1', '0', 0, '0', 0, now());
					这一行是新部署的 mysql 都有的, 清理的时候保留下来兼容刚部署 db 跑校验
				*/
				var cleanUpSQL string
				cleanUpSQL = fmt.Sprintf(
					"DELETE FROM `%s`.`%s` WHERE NOT (master_ip = '0.0.0.0' AND master_port = 3306 AND db = 'test' AND tbl = 'test' AND lower_boundary = '1=1' AND upper_boundary = '1=1' AND this_crc = '0' AND this_cnt = 0 AND master_crc = '0' AND master_cnt = 0)",
					r.resultDB, r.resultTbl,
				)

				_, cleanUpErr = r.conn.ExecContext(context.Background(), cleanUpSQL)
				if cleanUpErr != nil {
					slog.Error("clean up retry run checksum", slog.String("error", cleanUpErr.Error()))
					return
				}
				slog.Info("clean up retry run checksum success", slog.String("sql", cleanUpSQL))

			},
		),
	).Do(
		func() error {
			isEmptyResultTbl, err := r.isEmptyResultTbl()
			if err != nil {
				slog.Error("run checksum", slog.String("error", err.Error()))
				return err
			}
			slog.Info("run checksum", slog.Bool("isEmptyResultTbl", isEmptyResultTbl))

			if isEmptyResultTbl {
				err := r.writeFakeResult(roundStartStr, roundStartStr, false)
				if err != nil {
					slog.Error("run checksum", slog.String("error", err.Error()))
					return err
				}
			}

			output, err, pterr := r.run()
			if err != nil {
				slog.Error("run checksum", slog.String("error", err.Error()))
				return err
			}
			if pterr != nil {
				slog.Error("run checksum", slog.String("error", pterr.Error()))
				return pterr
			}
			if output == nil {
				err := fmt.Errorf("output nil")
				slog.Error("run checksum", slog.String("error", err.Error()))
				return err
			}

			if len(output.Summaries) == 0 {
				return &EmptySummaryError{}
			}
			return nil
		},
	)

	return err
}

func (r *Checker) runDemand() error {
	output, err, pterr := r.run()
	if err != nil {
		slog.Error("run checksum", slog.String("error", err.Error()))
		return err
	}
	if pterr != nil {
		slog.Error("run checksum", slog.String("error", pterr.Error()))
		return pterr
	}
	if output == nil {
		err := fmt.Errorf("output nil")
		slog.Error("run checksum", slog.String("error", err.Error()))
		return err
	}

	zipOutput, err := output.ZipString()
	if err != nil {
		slog.Error("run checksum", slog.String("error", err.Error()))
		return err
	}

	fmt.Println(zipOutput)
	return nil
}

func (r *Checker) isEmptyResultTbl() (bool, error) {
	var resultCnt int
	err := r.db.QueryRow(
		fmt.Sprintf(
			"SELECT COUNT(*) FROM %s.%s WHERE master_ip = ? AND master_port = ?",
			r.resultDB, r.resultTbl,
		),
		r.Config.Ip, r.Config.Port,
	).Scan(&resultCnt)
	if err != nil {
		slog.Error("check result table is empty", slog.String("error", err.Error()))
		return false, err
	}

	return resultCnt == 0, nil
}

func (r *Checker) writeFakeResult(fakeDB string, fakeTbl string, demand bool) error {
	// 为了兼容 flashback, 这里拼上库前缀
	resTable := r.resultHistoryTable
	if demand {
		resTable = r.resultTbl
	}

	ctx := context.Background()
	var globalBinlogFormat string
	err := r.conn.QueryRowxContext(ctx, `SELECT @@global.binlog_format`).Scan(&globalBinlogFormat)
	if err != nil {
		slog.Error("get global binlog format failed", slog.String("error", err.Error()))
		return err
	}
	if strings.ToUpper(globalBinlogFormat) == "ROW" {
		slog.Info("switch binlog format to row")

		var binlogFormatOld string
		err = r.conn.QueryRowxContext(ctx, `SELECT @@session.binlog_format`).Scan(&binlogFormatOld)
		if err != nil {
			slog.Error("get session binlog_format", slog.String("error", err.Error()))
			return err
		}

		_, err = r.conn.ExecContext(ctx, `SET SESSION binlog_format='ROW'`)
		if err != nil {
			slog.Error("set session binlog_format to ROW", slog.String("error", err.Error()))
			return err
		}
		defer func() {
			_, restoreErr := r.conn.ExecContext(
				ctx,
				fmt.Sprintf("SET SESSION binlog_format='%s'", binlogFormatOld),
			)
			if restoreErr != nil {
				slog.Error(
					"restore session binlog_format",
					slog.String("binlog_format", binlogFormatOld),
					slog.String("error", restoreErr.Error()),
				)
			}
		}()
	} else {
		slog.Info("skip switch binlog format", slog.String("global.binlog_format", globalBinlogFormat))
	}

	ts := time.Now().Format("2006-01-02 15:04:05")
	_, err = r.conn.ExecContext(
		ctx,
		fmt.Sprintf(
			"REPLACE INTO %s.%s("+
				"master_ip, master_port, "+
				"`db`, tbl, chunk, chunk_time, chunk_index, "+
				"lower_boundary, upper_boundary, "+
				"this_crc, this_cnt, master_crc, master_cnt, ts) "+
				"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
			r.resultDB,
			resTable,
		),
		r.Config.Ip, r.Config.Port,
		fakeDB, fakeTbl, 0, 0, "",
		"1=1", "1=1",
		0, 0, 0, 0, ts,
	)
	if err != nil {
		slog.Error(
			"write fake result row", slog.String("fake db", fakeDB), slog.String("fake tbl", fakeTbl),
			slog.Bool("demand", demand), slog.String("error", err.Error()), slog.String("ts", ts),
		)
		return err
	}
	slog.Info(
		"write fake result row", slog.String("fake db", fakeDB), slog.String("fake tbl", fakeTbl),
		slog.Bool("demand", demand), slog.String("ts", ts),
	)

	return nil
}

func (r *Checker) run() (output *Output, err error, pterr error) {
	var stdout, stderr bytes.Buffer

	ctx, cancel := context.WithCancel(context.Background())
	r.cancel = cancel

	extLibDir := filepath.Join(filepath.Dir(r.Config.PtChecksum.Path), "lib")
	command := exec.CommandContext(
		ctx, "perl", append(
			[]string{
				fmt.Sprintf("-I%s", extLibDir),
				r.Config.PtChecksum.Path,
			}, r.args...,
		)...,
	)
	command.Stdout = &stdout
	command.Stderr = &stderr
	slog.Info("build command", slog.String("pt-table-checksum command", command.String()))

	r.startTS = time.Now() // .In(time.Local)
	slog.Info("sleep 2s")
	time.Sleep(2 * time.Second) // 故意休眠 2s, 让时间往前走一下, mysql 时间戳精度不够, 这里太快了会有问题
	err = command.Run()

	/*
			pt-table-checksum 退出码解析已迁移至 pt_result.go 的 HandlePtChecksumResult。
			详见该文件注释; 旧实现存在以下问题, 故整体注释保留备查:
			  - exit 255 未处理, collectFlags(255) 会把所有 flag 误报
			  - ALREADY_RUNNING(2)/CAUGHT_SIGNAL(4) 依赖 stderr 非空才返回 pterr, 可能漏报
			  - 业务 flag (TABLE_DIFF/SKIP_CHUNK 等) 与 fatal 边界不清晰
			下方 if err != nil 的非 ExitError 提前 return 也已由 HandlePtChecksumResult 统一处理。

		if err != nil {
			var exitError *exec.ExitError
			if !errors.As(err, &exitError) {
				slog.Error("run pt-table-checksum got unexpected error", slog.String("error", err.Error()))
				return nil, err, nil
			}
		}

		var ptErr *exec.ExitError
		_ = errors.As(err, &ptErr)
		if ptErr != nil {
			slog.Info("run pt-table-checksum success", slog.String("pt err", ptErr.String()))
		} else {
			slog.Info("run pt-table-checksum success without any err")
		}

		var eLines []string
		if stderr.Len() > 0 {
			scanner := bufio.NewScanner(strings.NewReader(stderr.String()))
			scanner.Split(bufio.ScanLines)
			for scanner.Scan() {
				line := scanner.Text()
				line = strings.TrimSpace(line)
				if line != "" && !strings.Contains(line, "There is no good index and the table is oversized") {
					eLines = append(eLines, line)
				}
			}
		}

		ptFlags := make([]PtExitFlag, 0)
		if ptErr != nil {
			ptFlags = collectFlags(ptErr)
		}

		summaries, err := summary(stdout.String())
		if err != nil {
			slog.Error(
				"trans pt-table-checksum stdout to summary",
				slog.String("error", err.Error()),
				slog.String("pt stdout", stdout.String()),
			)
			return nil, err, nil
		}
		slog.Info("checksum summary", slog.String("summary", stdout.String()))

		output = &Output{
			PtStderr:    stderr.String(),
			Summaries:   summaries,
			PtExitFlags: ptFlags,
		}

		if ptErr != nil && (ptErr.ExitCode()&2 != 0 || ptErr.ExitCode()&4 != 0) {
			pterr = errors.New(output.String())
			if len(eLines) > 0 {
				slog.Error(
					"run pt-table-checksum bad flag found",
					slog.String("error", strings.Join(eLines, "\n")),
				)
				_, _ = fmt.Fprintf(os.Stderr, output.String())
				return output, nil, pterr
			}
		}

		return output, nil, nil
	*/

	// command.Run() 的 err 原样传入: exit 0 为 nil, exit 非 0 为 *exec.ExitError, 其余为 Go 执行错误。
	// HandlePtChecksumResult 负责 stdout/stderr 解析、exit flag 分类和 fatal 判定。
	return HandlePtChecksumResult(stdout.String(), stderr.String(), err)
}
