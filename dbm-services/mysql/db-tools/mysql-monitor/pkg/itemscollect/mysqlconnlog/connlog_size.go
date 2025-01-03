// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlconnlog

import (
	"fmt"
	"io/fs"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"

	"github.com/jmoiron/sqlx"
)

func mysqlConnLogSize(db *sqlx.DB) (string, error) {
	var dataDir string
	err := db.QueryRowx(`SELECT @@datadir`).Scan(&dataDir)
	if err != nil {
		slog.Error("select @@datadir", slog.String("error", err.Error()))
		return "", err
	}

	var logSize int64

	slog.Debug("statistic conn log", slog.String("path", filepath.Join(dataDir, cst.DBASchema)))
	err = filepath.WalkDir(
		filepath.Join(dataDir, cst.DBASchema),
		func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				slog.Error("statistic conn log size",
					slog.String("error", err.Error()),
					slog.String("path", path),
				)
				return filepath.SkipDir
			}

			slog.Debug("statistic conn log size", slog.String("path", path))
			if strings.HasPrefix(filepath.Base(path), "conn_log") {
				st, sterr := os.Stat(path)
				if sterr != nil {
					return filepath.SkipDir
				}
				if !st.IsDir() {
					slog.Debug(
						"statistic conn log size",
						slog.Any("status", st),
					)
					logSize += st.Size()
				}
			}
			return nil
		},
	)
	if err != nil {
		slog.Error("statistic conn log size", slog.String("error", err.Error()))
		return "", err
	}
	slog.Info("statistic conn log size", slog.Int64("size", logSize))

	if logSize >= sizeLimit {
		_, err = db.Exec(`SET GLOBAL INIT_CONNECT = ''`)
		if err != nil {
			slog.Error("disable init_connect",
				slog.String("error", err.Error()),
				slog.Int64("size", logSize),
			)
			return "", err
		}
		return fmt.Sprintf("too big connlog table size %d", logSize), nil
	}
	return "", nil
}
