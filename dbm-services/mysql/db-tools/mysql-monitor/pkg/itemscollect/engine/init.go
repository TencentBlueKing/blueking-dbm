// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package engine

import (
	"database/sql"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"regexp"
	"slices"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var executable string

var name = "engine"

var partitionPattern *regexp.Regexp

var systemDBs = []string{
	"mysql",
	"sys",
	"information_schema",
	"infodba_schema",
	"performance_schema",
	"test",
	"db_infobase",
}

// Checker TODO
type Checker struct {
	db *sqlx.DB
}

func init() {
	executable, _ = os.Executable()
	partitionPattern = regexp.MustCompile(`^(.*)#[pP]#.*\.ibd`)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	var report = &engineReport{}

	regFilePath := filepath.Join(
		filepath.Dir(executable),
		fmt.Sprintf("table-engine-count-%d.reg", config.MonitorConfig.Port),
	)
	regFile, err := os.OpenFile(
		regFilePath,
		os.O_CREATE|os.O_TRUNC|os.O_RDWR,
		0777)
	if err != nil {
		return "", errors.Wrap(err, "failed to open reg file")
	}
	defer func() {
		jsonString, _ := json.Marshal(*report)
		_, _ = regFile.WriteString(fmt.Sprintf("%s\n", jsonString))
		_ = regFile.Close()
	}()

	var dataDir sql.NullString
	err = c.db.Get(&dataDir, `SELECT @@datadir`)
	if err != nil {
		slog.Error("ibd-statistic", slog.String("error", err.Error()))
		return "", err
	}

	if !dataDir.Valid {
		err := errors.Errorf("invalid datadir: '%s'", dataDir.String)
		slog.Error("ibd-statistic", slog.String("error", err.Error()))
		return "", err
	}
	slog.Info("engine", slog.String("datadir", dataDir.String))

	report, err = c.idEngine(dataDir.String)
	if err != nil {
		return "", err
	}

	sid := slices.IndexFunc(report.Summaries, func(summary *engineSummary) bool {
		return summary.Engine == MyISAMEngine
	})

	if sid >= 0 && report.Summaries[sid].Count > 0 {
		dtid := slices.IndexFunc(report.Details, func(detail *engineDetail) bool {
			return detail.Engine == MyISAMEngine
		})
		msg = fmt.Sprintf(
			"%d myisam table found: %v",
			report.Summaries[sid].Count, report.Details[dtid],
		)
	}

	return msg, nil
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{db: cc.MySqlDB}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
