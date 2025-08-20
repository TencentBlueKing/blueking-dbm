package checker

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"fmt"
	"log/slog"

	"github.com/avast/retry-go/v4"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

type emptyOutputSummaryError struct {
}

func (e *emptyOutputSummaryError) Error() string {
	return "empty output summary"
}

func (r *Checker) RunV2() (err error) {
	err = r.preRunCommon()
	if err != nil {
		return err
	}

	var output *Output
	var pterr error

	switch r.Mode {
	case config.DemandMode:
		output, err, pterr = r.demandRun()
	case config.GeneralMode:
		output, err, pterr = r.generalRun()
	}

	if err != nil {
		return err
	}

	if output != nil {
		fmt.Println(output.String())
	}

	if pterr != nil {
		return pterr
	}

	return nil
}

func (r *Checker) preRunCommon() error {
	_, err := r.conn.ExecContext(
		context.Background(),
		fmt.Sprintf(`DELETE FROM %s.%s WHERE ts < NOW() - INTERVAL 10 DAY`, config.ResultDb, config.ResultHistoryTable),
	)
	if err != nil {
		return err
	}

	return nil
}

func (r *Checker) demandRun() (output *Output, err error, pterr error) {
	output, err, pterr = r.run()
	if err != nil {
		return nil, err, nil
	}
	if output == nil {
		return nil, fmt.Errorf("output is nil"), nil
	}

	ticketId := viper.GetInt64("ticket-id")
	err = r.moveResult(ticketId)
	if err != nil {
		return nil, err, nil
	}

	_, err = r.conn.ExecContext(
		context.Background(),
		fmt.Sprintf(`DELETE FROM %s.%s WHERE ticket_id = ?`, config.ResultDb, config.ResultTable), ticketId,
	)
	if err != nil {
		return nil, err, nil
	}

	return output, err, pterr
}

func (r *Checker) generalRun() (output *Output, err error, pterr error) {
	if r.Mode == config.GeneralMode && !config.ChecksumConfig.Enable {
		return nil, nil, nil
	}

	var existedResultCount int
	err = r.db.QueryRow(
		fmt.Sprintf(`SELECT COUNT(*) FROM %s.%s WHERE ticket_id = 0`,
			config.ResultDb, config.ResultTable),
	).Scan(&existedResultCount)
	if err != nil {
		return nil, err, nil
	}
	slog.Info("general run", slog.Int("legacy checksum result", existedResultCount))

	err = r.writeFakeResult(dailyStr, dailyStr)
	if err != nil {
		return nil, err, nil
	}

	if existedResultCount == 0 {
		err = r.writeFakeResult(roundStartStr, roundStartStr)
		if err != nil {
			return nil, err, nil
		}
	}

	err = retry.Do(
		func() error {
			output, err, pterr = r.run()
			if err != nil {
				return err
			}
			if output == nil {
				return fmt.Errorf("output is nil")
			}
			slog.Info("general run", slog.Any("output", output))

			if len(output.Summaries) == 0 && existedResultCount > 0 {
				_, err = r.db.Exec(
					fmt.Sprintf(`DELETE FROM %s.%s WHERE ticket_id = 0 AND master_ip = ? AND master_port = ?`, config.ResultDb, config.ResultTable),
					r.Config.Ip, r.Config.Port,
				)
				if err != nil {
					return err
				}
				err = r.writeFakeResult(roundStartStr, roundStartStr)
				if err != nil {
					return err
				}
				return &emptyOutputSummaryError{}
			}
			return nil
		},
		retry.RetryIf(func(err error) bool {
			slog.Info(
				"general run",
				slog.String("retry if input error", err.Error()),
				slog.Bool("error check", errors.Is(err, &emptyOutputSummaryError{})),
			)
			if errors.Is(err, &emptyOutputSummaryError{}) && existedResultCount > 0 {
				slog.Info("general run retry")
				return true
			}
			slog.Info("general run do not retry")
			return false
		}),
		retry.OnRetry(func(n uint, err error) {
			slog.Info("general run", slog.Int("times", int(n)), slog.String("with error", err.Error()))
		}),
		retry.Attempts(2),
	)
	if err != nil {
		return nil, err, nil
	}

	err = r.moveResult(0)
	if err != nil {
		return nil, err, nil
	}

	return output, err, pterr
}
