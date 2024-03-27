package checker

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

var roundStartStr = "_dba_fake_round_start"

func (r *Checker) Run() error {
	//isEmptyResultTbl, err := r.isEmptyResultTbl()
	//if err != nil {
	//	return err
	//}
	//if isEmptyResultTbl {
	//	err := r.writeFakeResult(roundStartStr, roundStartStr)
	//	if err != nil {
	//		slog.Error("write round start", slog.String("error", err.Error()))
	//		return err
	//	}
	//	slog.Info("round start")
	//}

	stackDepth := 0

RunCheckLabel:
	slog.Info("run", slog.Int("stack depth", stackDepth))
	stackDepth += 1
	if stackDepth > 2 {
		err := fmt.Errorf("retry stack too deep: %d", stackDepth)
		slog.Error("run stack check", slog.String("error", err.Error()))
		return err
	}

	output, err, pterr := r.run()
	if err != nil {
		return err
	}

	if r.Mode == config.GeneralMode {
		slog.Info("run in general mode")

		isEmptyResultTbl, err := r.isEmptyResultTbl()
		if err != nil {
			return err
		}
		if isEmptyResultTbl {
			err := r.writeFakeResult(roundStartStr, roundStartStr)
			if err != nil {
				slog.Error("write round start", slog.String("error", err.Error()))
				return err
			}
			slog.Info("round start")
		}

		// 校验摘要是空的, 有两种可能
		// 1. 应用过滤器后, 没有库表需要校验
		// 2. checksum 中有所有库表的校验结果, 这一轮轮空了
		if len(output.Summaries) == 0 {
			slog.Info("run got empty summary")

			var cnt int
			err := r.db.QueryRow(fmt.Sprintf("SELECT count(*) FROM %s.%s", r.resultDB, r.resultTbl)).Scan(&cnt)
			if err != nil {
				slog.Error("query result table rows count", slog.String("error", err.Error()))
				return err
			}
			slog.Info("query result table rows count", slog.Int("rows count", cnt))
			/*
				由于会写入 round start 假数据
				所以如果行数大于 1, 则说明有真实的校验结果
				完成了一轮
			*/
			if cnt > 1 {
				//Replicate 是带有库前缀的字符串
				_, err := r.db.Exec(fmt.Sprintf(`TRUNCATE TABLE %s`, r.Config.PtChecksum.Replicate))
				if err != nil {
					slog.Error(
						"truncate regular result table",
						slog.String("error", err.Error()),
						slog.String("table name", r.Config.PtChecksum.Replicate),
					)
					return err
				}

				// 清掉上一轮的结构后再跑一次
				slog.Info("clear last round result and run again")
				goto RunCheckLabel
			} else {
				// 什么都没干, 又没有库表需要校验
				// 直接返回
				return nil
			}
		}

		err = r.moveResult()
		if err != nil {
			return err
		}
	} else {
		slog.Info("run in demand mode")
	}

	fmt.Println(output.String())

	if pterr != nil {
		return pterr
	}

	return nil
}

func (r *Checker) isEmptyResultTbl() (bool, error) {
	var resultCnt int
	err := r.db.QueryRow(fmt.Sprintf("SELECT COUNT(*) FROM %s.%s", r.resultDB, r.resultTbl)).Scan(&resultCnt)
	if err != nil {
		slog.Error("check result table is empty", slog.String("error", err.Error()))
		return false, err
	}

	return resultCnt == 0, nil
}

func (r *Checker) writeFakeResult(fakeDB string, fakeTbl string) error {
	conn, err := r.db.Connx(context.Background())
	if err != nil {
		slog.Error("get conn from sqlx.db", slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = conn.Close()
	}()

	_, err = conn.ExecContext(context.Background(), `SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;`)
	if err != nil {
		slog.Error("set iso level", slog.String("error", err.Error()))
		return err
	}

	//防止 row 格式的 replace 阻塞 slave 同步
	_, err = conn.ExecContext(context.Background(), `set binlog_format='statement'`)
	if err != nil {
		slog.Error(
			"set binlog format to statement before insert fake result", slog.String("error", err.Error()))
		return err
	}

	// 为了兼容 flashback, 这里拼上库前缀
	ts := time.Now()
	_, err = conn.ExecContext(
		context.Background(),
		fmt.Sprintf("REPLACE INTO %s.%s("+
			"master_ip, master_port, "+
			"`db`, tbl, chunk, chunk_time, chunk_index, "+
			"lower_boundary, upper_boundary, "+
			"this_crc, this_cnt, master_crc, master_cnt, ts) "+
			"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
			r.resultDB,
			r.resultHistoryTable),
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

	// stderr.Reset()
	command := exec.CommandContext(ctx, r.Config.PtChecksum.Path, r.args...)
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

		1, 2, 4 肯定要当错误, 其他的先扔回去?
	*/
	if stderr.Len() > 0 {
		err = errors.New(stderr.String())
		slog.Error("run pt-table-checksum got un-docoument error", slog.String("error", err.Error()))
		return nil, err, nil
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

	if ptErr != nil && (ptErr.ExitCode()&1 != 0 || ptErr.ExitCode()&2 != 0 || ptErr.ExitCode()&4 != 0) {
		pterr = errors.New(output.String())
		slog.Error("run pt-table-checksum bad flag found", slog.String("error", err.Error()))
		_, _ = fmt.Fprintf(os.Stderr, output.String())
		return output, nil, pterr
	}

	return output, nil, nil
}
