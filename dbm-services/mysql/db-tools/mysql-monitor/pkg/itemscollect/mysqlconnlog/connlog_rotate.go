// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlconnlog

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/juju/ratelimit"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

// mysqlConnLogRotate TODO
/*
1. binlog 是 session 变量, 所以只需要禁用就行了
*/
func mysqlConnLogRotate(db *sqlx.DB) (string, error) {
	conn, err := prepareRotate(db)
	if err != nil {
		return "", err
	}
	defer func() {
		_ = conn.Close()
	}()

	err = report(conn)
	if err != nil {
		return "", err
	}

	err = clean(conn)
	if err != nil {
		return "", err
	}
	return "", nil
}

func prepareRotate(db *sqlx.DB) (conn *sqlx.Conn, err error) {
	conn, err = db.Connx(context.Background())
	if err != nil {
		slog.Error("connlog rotate get conn from db", slog.String("error", err.Error()))
		return nil, err
	}

	var _r interface{}
	err = conn.GetContext(context.Background(), &_r,
		`SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
					WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND TABLE_TYPE='BASE TABLE'`,
		cst.DBASchema, "conn_log")
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			err = errors.Errorf("conn_log table not found")
			slog.Error(err.Error())
			return nil, err
		} else {
			slog.Error("check conn_log exists", slog.String("error", err.Error()))
			return nil, err
		}
	}

	_, err = conn.ExecContext(context.Background(), `SET SQL_LOG_BIN=0`)
	if err != nil {
		slog.Error("disable binlog", slog.String("error", err.Error()))
		return nil, err
	}
	slog.Info("rotate conn log disable binlog success")

	return
}

func report(conn *sqlx.Conn) error {
	reportFilePath := filepath.Join(cst.DBAReportBase, "mysql", "conn_log", "report.log")
	err := os.MkdirAll(filepath.Dir(reportFilePath), 0755)
	if err != nil {
		slog.Error("make report dir", slog.String("error", err.Error()))
		return err
	}
	slog.Info("make report dir", slog.String("dir", filepath.Dir(reportFilePath)))

	f, err := os.OpenFile(
		reportFilePath,
		os.O_CREATE|os.O_TRUNC|os.O_RDWR,
		0755,
	)
	if err != nil {
		slog.Error("open conn log report file", slog.String("error", err.Error()))
		return err
	}
	slog.Info("open conn report file", slog.String("file path", f.Name()))

	lf := ratelimit.Writer(f, ratelimit.NewBucketWithRate(float64(speedLimit), speedLimit))

	rows, err := conn.QueryxContext(
		context.Background(),
		fmt.Sprintf(
			`SELECT * FROM %s.conn_log WHERE conn_time >= DATE_SUB(NOW(), INTERVAL 1 DAY)`,
			cst.DBASchema,
		),
	)
	if err != nil {
		slog.Error("query conn_log", slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = rows.Close()
	}()

	for rows.Next() {
		cr := connRecord{
			BkBizId:      config.MonitorConfig.BkBizId,
			BkCloudId:    config.MonitorConfig.BkCloudID,
			ImmuteDomain: config.MonitorConfig.ImmuteDomain,
			Port:         config.MonitorConfig.Port,
			MachineType:  config.MonitorConfig.MachineType,
			Role:         config.MonitorConfig.Role,
		}
		err := rows.StructScan(&cr)
		if err != nil {
			slog.Error("scan conn_log record", slog.String("error", err.Error()))
			return err
		}

		content, err := json.Marshal(cr)
		if err != nil {
			slog.Error("marshal conn record", slog.String("error", err.Error()))
			return err
		}

		_, err = lf.Write(append(content, []byte("\n")...))
		if err != nil {
			slog.Error("write conn report", slog.String("error", err.Error()))
			return err
		}
	}

	return nil
}

func clean(conn *sqlx.Conn) error {
	for {
		rowsDeleted, err := cleanOneRound(conn)
		if err != nil {
			return err
		}

		slog.Info("clean 3days ago conn_log limit 500")

		if rowsDeleted == 0 {
			break
		}
	}

	slog.Info("clean 3days ago conn_log")
	return nil
}

func cleanOneRound(conn *sqlx.Conn) (affectedRows int64, err error) {
	r, err := conn.ExecContext(
		context.Background(),
		fmt.Sprintf(
			`DELETE FROM %s.conn_log WHERE conn_time < DATE_SUB(NOW(), INTERVAL 3 DAY) LIMIT 500`,
			cst.DBASchema,
		),
	)
	if err != nil {
		slog.Error("clean 3days ago conn_log", slog.String("error", err.Error()))
		return 0, err
	}

	rowsDeleted, err := r.RowsAffected()
	if err != nil {
		slog.Error("clean 3days ago conn_log", slog.String("error", err.Error()))
		return 0, err
	}

	return rowsDeleted, nil
}
