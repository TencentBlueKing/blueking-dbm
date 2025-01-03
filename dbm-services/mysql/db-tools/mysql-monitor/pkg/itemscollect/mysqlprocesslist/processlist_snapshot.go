// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlprocesslist

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
)

type mysqlProcess struct {
	Id      sql.NullInt64  `db:"ID" json:"id"`
	User    sql.NullString `db:"USER" json:"user"`
	Host    sql.NullString `db:"HOST" json:"host"`
	Db      sql.NullString `db:"DB" json:"db"`
	Command sql.NullString `db:"COMMAND" json:"command"`
	Time    sql.NullInt64  `db:"TIME" json:"time"`
	State   sql.NullString `db:"STATE" json:"state"`
	Info    sql.NullString `db:"INFO" json:"info"`
}

func (c *mysqlProcess) JsonString() (string, error) {
	content, err := json.Marshal(
		struct {
			Id      int64  `json:"id"`
			User    string `json:"user"`
			Host    string `json:"host"`
			Db      string `json:"db"`
			Command string `json:"command"`
			Time    int64  `json:"time"`
			State   string `json:"state"`
			Info    string `json:"info"`
		}{
			Id:      c.Id.Int64,
			User:    c.User.String,
			Host:    c.Host.String,
			Db:      c.Db.String,
			Command: c.Command.String,
			Time:    c.Time.Int64,
			State:   c.State.String,
			Info:    c.Info.String,
		},
	)

	if err != nil {
		slog.Error("marshal process list", slog.String("error", err.Error()))
		return "", err
	}

	return string(content), nil
}

func snapShot(db *sqlx.DB) error {
	processList, err := queryProcessList(db)
	if err != nil {
		return err
	}

	regFilePath := filepath.Join(
		filepath.Dir(executable),
		fmt.Sprintf("processlist.%d.reg", config.MonitorConfig.Port))
	f, err := os.OpenFile(
		regFilePath,
		os.O_CREATE|os.O_TRUNC|os.O_RDWR,
		0755,
	)
	if err != nil {
		slog.Error(
			"create processlist reg file",
			slog.String("error", err.Error()),
			slog.String("file path", regFilePath),
		)
		return err
	}

	content, err := json.Marshal(processList)
	if err != nil {
		slog.Error("marshal processlist", slog.String("error", err.Error()))
		return err
	}

	_, err = f.Write(content)
	if err != nil {
		slog.Error("write processlist.reg", slog.String("error", err.Error()))
		return err
	}

	return nil
}

func loadSnapShot() ([]*mysqlProcess, error) {
	content, err := os.ReadFile(
		filepath.Join(
			filepath.Dir(executable),
			fmt.Sprintf("processlist.%d.reg", config.MonitorConfig.Port),
		),
	)
	if err != nil {
		slog.Error("read processlist.reg", slog.String("error", err.Error()))
		return nil, err
	}

	var res []*mysqlProcess
	err = json.Unmarshal(content, &res)
	if err != nil {
		slog.Error("unmarshal processlist", slog.String("error", err.Error()))
		return nil, err
	}

	return res, nil
}

func queryProcessList(db *sqlx.DB) ([]mysqlProcess, error) {
	rows, err := db.Queryx(
		`SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO FROM INFORMATION_SCHEMA.PROCESSLIST`)
	if err != nil {
		slog.Error("show full processlist", slog.String("error", err.Error()))
		return nil, err
	}
	defer func() {
		_ = rows.Close()
	}()

	var res []mysqlProcess
	for rows.Next() {
		p := mysqlProcess{}
		err := rows.StructScan(&p)
		if err != nil {
			slog.Error("scan processlist", slog.String("error", err.Error()))
			return nil, err
		}
		res = append(res, p)
	}

	return res, nil
}
