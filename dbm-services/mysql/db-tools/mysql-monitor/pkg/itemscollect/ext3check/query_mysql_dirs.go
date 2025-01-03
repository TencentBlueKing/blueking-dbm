// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ext3check

import (
	"database/sql"
	"fmt"
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/shopspring/decimal"
	"gopkg.in/ini.v1"
)

func mysqlDirs(db *sqlx.DB, variables []string) (dirs []string, err error) {
	var datadir string

	for _, v := range variables {
		var dir sql.NullString
		err = db.Get(&dir, fmt.Sprintf(`SELECT @@%s`, v))
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
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

	var versionStr string
	err = db.Get(&versionStr, `SELECT SUBSTRING_INDEX(@@version, ".", 2)`)
	if err != nil {
		return nil, errors.Wrap(err, `SELECT SUBSTRING_INDEX(@@version, ".", 2)`)
	}
	version, err := decimal.NewFromString(versionStr)
	if err != nil {
		return nil, errors.Wrapf(err, "new decimal from %s", versionStr)
	}

	if version.GreaterThanOrEqual(decimal.NewFromFloat(5.6)) {
		var binlogBase sql.NullString
		var relaylogBase sql.NullString

		err = db.Get(&binlogBase, `SELECT @@log_bin_basename`)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return nil, errors.Wrap(err, `SELECT @@log_bin_basename`)
		}

		if binlogBase.Valid {
			dirs = append(dirs, filepath.Dir(binlogBase.String))
		}

		err = db.Get(&relaylogBase, `SELECT @@relay_log_basename`)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return nil, errors.Wrap(err, `SELECT @@relay_log_basename`)
		}

		if relaylogBase.Valid {
			dirs = append(dirs, filepath.Dir(relaylogBase.String))
		}

	} else {
		var myCnfPath string
		if config.MonitorConfig.Port == 3306 {
			myCnfPath = "/etc/my.cnf"
		} else {
			myCnfPath = fmt.Sprintf("/etc/my.cnf.%d", config.MonitorConfig.Port)
		}

		myCnf, err := ini.LoadSources(ini.LoadOptions{
			PreserveSurroundedQuote: true,
			IgnoreInlineComment:     true,
			AllowBooleanKeys:        true,
			AllowShadows:            true,
		}, myCnfPath)
		if err != nil {
			return nil, errors.Wrapf(err, "load %s failed", myCnfPath)
		}

		logBin := myCnf.Section("mysqld").Key("log_bin").String()
		relayLog := myCnf.Section("mysqld").Key("relay_log").String()

		dirs = append(dirs, filepath.Dir(logBin))
		dirs = append(dirs, filepath.Dir(relayLog))
	}

	for i, dir := range dirs {
		if !filepath.IsAbs(dir) {
			dirs[i] = filepath.Join(datadir, dir)
		}
	}

	return dirs, nil
}
