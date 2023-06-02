// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ext3check

import (
	"context"
	"database/sql"
	"fmt"
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

func mysqlDirs(db *sqlx.DB, variables []string) (dirs []string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var datadir string

	for _, v := range variables {
		var dir sql.NullString
		err = db.GetContext(ctx, &dir, fmt.Sprintf(`SELECT @@%s`, v))
		if err != nil && err != sql.ErrNoRows {
			return nil, errors.Wrap(err, fmt.Sprintf(`SELECT @@%s`, v))
		}

		// mysql其他的目录可能是以 datadir 为 base, 所以要单独存一下
		if dir.Valid {
			dirs = append(dirs, dir.String)
			if v == "datadir" {
				datadir = dir.String
			}
		}
	}

	var binlogBase sql.NullString
	err = db.GetContext(ctx, &binlogBase, `SELECT @@log_bin_basename`)
	if err != nil && err != sql.ErrNoRows {
		return nil, errors.Wrap(err, `SELECT @@log_bin_basename`)
	}

	if binlogBase.Valid {
		dirs = append(dirs, filepath.Dir(binlogBase.String))
	}

	var relaylogBase sql.NullString
	err = db.GetContext(ctx, &relaylogBase, `SELECT @@relay_log_basename`)
	if err != nil && err != sql.ErrNoRows {
		return nil, errors.Wrap(err, `SELECT @@relay_log_basename`)
	}

	if relaylogBase.Valid {
		// fmt.Printf("relay-log: %s\n", filepath.Dir(relaylogBase.String))
		dirs = append(dirs, filepath.Dir(relaylogBase.String))
	}

	for i, dir := range dirs {
		if !filepath.IsAbs(dir) {
			dirs[i] = filepath.Join(datadir, dir)
		}
	}

	return dirs, nil
}
