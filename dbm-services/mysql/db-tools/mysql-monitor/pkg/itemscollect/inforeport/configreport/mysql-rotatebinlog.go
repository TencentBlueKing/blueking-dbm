// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package configreport

import (
	"encoding/json"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/pkg/errors"

	actorCst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
)

// ReportRotatebinlogConfig 上报 rotatebinlog 配置（主机级别，不区分端口）
// 不同端口上报的都是同一份 main.yaml，所以 port 固定为 0
// 仅当配置文件 mtime 变化或距上次写入超过 24 小时时才写入 local_config 和上报日志
// 配置文件不存在时删除 local_config 中对应的行
func ReportRotatebinlogConfig(dbPort int, db *pkg.MySQLMonitorDBH) error {
	confFile := filepath.Join(actorCst.MysqlRotateBinlogInstallPath, "main.yaml")
	cfg := &ModelLocalConfig{
		Host:      config.MonitorConfig.Ip,
		Port:      0, // 主机级配置，port 固定为 0
		ConfType:  "backup",
		ConfFile:  "binlog_rotate.yaml",
		ConfigKey: "",
	}

	fi, err := os.Stat(confFile)
	if err != nil {
		if os.IsNotExist(err) {
			return DeleteLocalConfig(db, cfg)
		}
		return err
	}
	cfg.ConfMtime = fi.ModTime().Unix()

	needWrite, err := NeedWriteLocalConfig(db, cfg)
	if err != nil {
		return err
	}
	if !needWrite {
		slog.Debug("skip rotatebinlog config report, no change", slog.String("file", confFile))
		return nil
	}

	payload, err := buildRotatebinlogPayload(confFile)
	if err != nil {
		return err
	}
	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	body := string(bodyBytes)
	report, err := GetMixedReport("rotatebinlog_config_main.log")
	if err != nil {
		return err
	}
	event := NewDynamicEvent("rotatebinlog_config", "tendbha", 1)
	event.SetPayload(payload)
	report.Println(event)

	cfg.ConfigValue = body
	cfg.ClusterDomain = config.MonitorConfig.ImmuteDomain
	return ReplaceLocalConfig(db, cfg)
}

// buildRotatebinlogPayload 解析 rotatebinlog main.yaml，脱敏、收一级，并补充 EnableBackupClient
func buildRotatebinlogPayload(confFile string) (map[string]interface{}, error) {
	cnf, err := rotate.ReadMainConfig(confFile)
	if err != nil {
		return nil, err
	}
	masked, _, err := MaskedJSONPayload(cnf)
	if err != nil {
		return nil, err
	}
	m, ok := FlattenOneLevel(masked).(map[string]interface{})
	if !ok {
		return nil, errors.Errorf("unexpected rotatebinlog config format: %s", confFile)
	}
	copyKey(m, "public.backup_enable", "EnableBackupClient")
	return m, nil
}
