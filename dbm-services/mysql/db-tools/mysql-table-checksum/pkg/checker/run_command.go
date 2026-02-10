package checker

import (
	"bufio"
	"bytes"
	"context"

	"errors"
	"fmt"
	"log/slog"
	"os"
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
	case config.DemandMode:

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
		fmt.Sprintf(`DELETE FROM %s WHERE ts < NOW() - INTERVAL 10 DAY`, r.resultHistoryTable),
	)
	if err != nil {
		slog.Error("run checksum", slog.String("error", err.Error()))
	}
	return nil
}

func (r *Checker) runGeneral() error {
	var cleanUpErr error

	err := retry.New(
		retry.Attempts(2),
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
			func(_ uint, _ error) {
				// 查询MySQL版本，5.7版本使用DELETE，其他版本使用TRUNCATE TABLE
				var version string
				if err := r.db.QueryRow("SELECT VERSION()").Scan(&version); err != nil {
					slog.Error("query mysql version", slog.String("error", err.Error()))
					cleanUpErr = err
					return
				}

				var cleanUpSQL string
				if strings.HasPrefix(version, "5.7") {
					cleanUpSQL = fmt.Sprintf("DELETE FROM `%s`.`%s`", r.resultDB, r.resultTbl)
				} else {
					cleanUpSQL = fmt.Sprintf("TRUNCATE TABLE `%s`.`%s`", r.resultDB, r.resultTbl)
				}

				_, cleanUpErr = r.db.Exec(cleanUpSQL)
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

	ts := time.Now().Format("2006-01-02 15:04:05")
	_, err := r.conn.ExecContext(
		context.Background(),
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
		slog.Error("write fake result row", slog.String("error", err.Error()))
		return err
	}
	slog.Info("write fake result success")

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

	/*
		这一段是最难受的逻辑, 根据 pt-table-checksum 的文档

		pt-table-checksum has three possible exit statuses: zero, 255, and any other value is a bitmask with flags for different problems.

		A zero exit status indicates no errors, warnings, or checksum differences, or skipped chunks or tables.

		A 255 exit status indicates a fatal error. In other words: the tool died or crashed. The error is printed to STDERR.

		If the exit status is not zero or 255, then its value functions as a bitmask with these flags:
		... balabala...

		看起来似乎把错误都归类到各种 bit flag 了, 其实根本不是, 在它代码中有大量的 die, 这些全都不在文档描述的 flag 里面
		而它的这些 flag 又和系统的 errno 严重冲突, 所以照着文档写出来的错误捕捉根本不能用
		只能暴力的, 不管怎样, 只要有 stderr 就返回错误, 然后再按照 flag 来

		然而
		FLAG              BIT VALUE  MEANING
		================  =========  ==========================================
		ERROR                     1  A non-fatal error occurred
		ALREADY_RUNNING           2  --pid file exists and the PID is running
		CAUGHT_SIGNAL             4  Caught SIGHUP, SIGINT, SIGPIPE, or SIGTERM
		NO_SLAVES_FOUND           8  No replicas or cluster nodes were found
		TABLE_DIFF               16  At least one diff was found
		SKIP_CHUNK               32  At least one chunk was skipped
		SKIP_TABLE               64  At least one table was skipped
		REPLICATION_STOPPED     128  Replica is down or stopped

		这些 flag 咋办
		是当作错误抛出还是当作正常的执行结果返回给调用方, 让调用方自己去处理?

		1 不能当做错误, 表分块超时也会返回这个值
		2, 4 肯定要当错误, 其他的先扔回去?
	*/
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
}
