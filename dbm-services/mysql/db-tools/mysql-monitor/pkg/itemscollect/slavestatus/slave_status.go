// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package slavestatus

import (
	"context"
	"fmt"
	"log/slog"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var slaveStatusName = "slave-status"

type slaveStatusChecker struct {
	db          *sqlx.DB
	slaveStatus map[string]interface{}
}

// Run 运行
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
					slog.Error("collect slave errors", slog.String("error", err.Error()))
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
		slog.Error("show slave status", slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = rows.Close()
	}()

	for rows.Next() {
		err := rows.MapScan(s.slaveStatus)
		if err != nil {
			slog.Error("scan slave status", slog.String("error", err.Error()))
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

// Name 监控项名
func (s *slaveStatusChecker) Name() string {
	return slaveStatusName
}

// NewSlaveStatusChecker 新建监控项实例
func NewSlaveStatusChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &slaveStatusChecker{
		db:          cc.MySqlDB,
		slaveStatus: make(map[string]interface{}),
	}
}

// RegisterSlaveStatusChecker 注册监控项
func RegisterSlaveStatusChecker() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return slaveStatusName, NewSlaveStatusChecker
}
