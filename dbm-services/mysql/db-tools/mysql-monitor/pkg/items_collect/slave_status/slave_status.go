// Package slave_status TODO
package slave_status

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"
	"fmt"
	"strings"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

var slaveStatusName = "slave-status"

type slaveStatusChecker struct {
	db          *sqlx.DB
	slaveStatus map[string]interface{}
}

// Run TODO
func (s *slaveStatusChecker) Run() (msg string, err error) {
	err = s.fetchSlaveStatus()
	if err != nil {
		return "", err
	}

	if s.slaveStatus == nil || len(s.slaveStatus) == 0 {
		return "empty slave status", nil
	}

	if !s.isOk() {
		slaveErr, err := s.collectError()
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("IO/SQL thread not running: %s", slaveErr), nil
	}

	return "", nil
}

func (s *slaveStatusChecker) isOk() bool {
	return strings.ToUpper(s.slaveStatus["Slave_IO_Running"].(string)) == "YES" &&
		strings.ToUpper(s.slaveStatus["Slave_SQL_Running"].(string)) == "YES"
}

func (s *slaveStatusChecker) collectError() (string, error) {
	var slaveErrors []string
	for _, ek := range []struct {
		ErrKey   string
		ErrnoKey string
	}{
		{ErrKey: "Last_Error", ErrnoKey: "Last_Errno"},
		{ErrKey: "Last_SQL_Error", ErrnoKey: "Last_SQL_Errno"},
		{ErrKey: "Last_IO_Error", ErrnoKey: "Last_IO_Errno"},
	} {
		// 反射出来的都是字符串, 所以这里要做字符串对比
		if errNo, ok := s.slaveStatus[ek.ErrnoKey]; !ok {
			err := errors.Errorf("%s not found in slave status", ek.ErrnoKey)
			return "", err
		} else {
			slog.Debug(
				"collect slave errors",
				slog.String("key", ek.ErrnoKey), slog.String("value", errNo.(string)),
			)
			if errNo.(string) != "0" {
				if errMsg, ok := s.slaveStatus[ek.ErrKey]; !ok {
					err := errors.Errorf("%s not found in slave status", ek.ErrnoKey)
					slog.Error("collect slave errors", err)
					return "", err
				} else {
					slaveErr := fmt.Sprintf(
						`%s: %s [%s]`,
						ek.ErrKey,
						errMsg,
						errNo,
					)
					slaveErrors = append(
						slaveErrors,
						slaveErr,
					)
					slog.Debug("collect slave errors", slog.String("slave error", slaveErr))
				}
			}
		}
	}

	return strings.Join(slaveErrors, ","), nil
}

func (s *slaveStatusChecker) fetchSlaveStatus() error {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	rows, err := s.db.QueryxContext(ctx, `SHOW SLAVE STATUS`)
	if err != nil {
		slog.Error("show slave status", err)
		return err
	}
	defer func() {
		_ = rows.Close()
	}()

	for rows.Next() {
		err := rows.MapScan(s.slaveStatus)
		if err != nil {
			slog.Error("scan slave status", err)
			return err
		}
		break
	}

	for k, v := range s.slaveStatus {
		if value, ok := v.([]byte); ok {
			s.slaveStatus[k] = strings.TrimSpace(string(value))
		}
	}
	slog.Debug("slave status", slog.Any("status", s.slaveStatus))

	return nil
}

// Name TODO
func (s *slaveStatusChecker) Name() string {
	return slaveStatusName
}

// NewSlaveStatusChecker TODO
func NewSlaveStatusChecker(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &slaveStatusChecker{
		db:          cc.MySqlDB,
		slaveStatus: make(map[string]interface{}),
	}
}

// RegisterSlaveStatusChecker TODO
func RegisterSlaveStatusChecker() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return slaveStatusName, NewSlaveStatusChecker
}
