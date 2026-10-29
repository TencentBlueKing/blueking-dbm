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
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"

	actorCst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	checksumConfig "dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

// ReportChecksumConfig 按端口上报 checksum 配置
// 仅当配置文件 mtime 变化或距上次写入超过 24 小时时才写入 local_config 和上报日志
// 配置文件不存在时删除 local_config 中对应的行
func ReportChecksumConfig(dbPort int, db *pkg.MySQLMonitorDBH) error {
	confFile := filepath.Join(actorCst.ChecksumInstallPath, fmt.Sprintf("checksum_%d.yaml", dbPort))
	cfg := &ModelLocalConfig{
		Host:      config.MonitorConfig.Ip,
		Port:      dbPort,
		ConfType:  "checksum",
		ConfFile:  confFile,
		ConfigKey: "",
	}

	fi, err := os.Stat(confFile)
	if err != nil {
		if os.IsNotExist(err) {
			return DeleteLocalConfig(db, cfg)
		}
		return errors.WithMessagef(err, "stat %s", confFile)
	}
	cfg.ConfMtime = fi.ModTime().Unix()

	needWrite, err := NeedWriteLocalConfig(db, cfg)
	if err != nil {
		return err
	}
	if !needWrite {
		slog.Debug("skip checksum config report, no change", slog.String("file", confFile))
		return nil
	}

	content, err := os.ReadFile(confFile)
	if err != nil {
		return errors.WithMessagef(err, "read %s", confFile)
	}
	cnf := &checksumConfig.Config{Enable: true}
	if err = yaml.UnmarshalStrict(content, cnf); err != nil {
		return errors.WithMessagef(err, "parse %s", confFile)
	}
	masked, _, err := MaskedJSONPayload(cnf)
	if err != nil {
		return err
	}
	payload := FlattenOneLevel(masked)
	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	body := string(bodyBytes)

	report, err := GetMixedReport(fmt.Sprintf("checksum_config_%d.log", dbPort))
	if err != nil {
		return err
	}
	event := NewDynamicEvent("checksum_config", "tendbha", 1)
	event.SetPayload(payload)
	report.Println(event)

	cfg.ConfigValue = body
	cfg.ClusterDomain = config.MonitorConfig.ImmuteDomain
	cfg.ConfFile = filepath.Base(cfg.ConfFile) // 不用绝对路径
	return ReplaceLocalConfig(db, cfg)
}
