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
	"strings"

	actorCst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/cmd"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

// ReportDbbackupConfig 按端口上报 dbbackup 配置
// 仅当配置文件 mtime 变化或距上次写入超过 24 小时时才写入 local_config 和上报日志
// 配置文件不存在时删除 local_config 中对应的行
func ReportDbbackupConfig(dbPort int, db *pkg.MySQLMonitorDBH) error {
	confFile := filepath.Join(actorCst.DbbackupGoInstallPath, fmt.Sprintf("dbbackup.%d.ini", dbPort))
	cfg := &ModelLocalConfig{
		Host:      config.MonitorConfig.Ip,
		Port:      dbPort,
		ConfType:  "backup",
		ConfFile:  "dbbackup.ini",
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
		slog.Debug("skip dbbackup config report, no change", slog.String("file", confFile))
		return nil
	}

	payload, err := buildDbbackupPayload(confFile)
	if err != nil {
		return err
	}
	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	body := string(bodyBytes)
	report, err := GetMixedReport(fmt.Sprintf("dbbackup_config_%d.log", dbPort))
	if err != nil {
		return err
	}
	event := NewDynamicEvent("dbbackup_config", "tendbha", 1)
	event.SetPayload(payload)
	report.Println(event)

	cfg.ConfigValue = body
	cfg.ClusterDomain = config.MonitorConfig.ImmuteDomain
	return ReplaceLocalConfig(db, cfg)
}

// buildDbbackupPayload 解析 dbbackup.ini，脱敏、收一级，并补充角色维度的 DataSchemaGrant 和 EnableBackupClient
func buildDbbackupPayload(confFile string) (map[string]interface{}, error) {
	cnf, err := cmd.GetConfigForReport(confFile)
	if err != nil {
		return nil, err
	}
	masked, _, err := MaskedJSONPayload(cnf)
	if err != nil {
		return nil, err
	}
	m, ok := FlattenOneLevel(masked).(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("unexpected dbbackup config format: %s", confFile)
	}
	addRoleDataSchemaGrant(m, cnf.Public.MysqlRole)
	copyKey(m, "BackupClient.EnableBackupClient", "EnableBackupClient")
	return m, nil
}

// roleDataSchemaGrantPrefix dbbackup MysqlRole（小写）→ 角色维度的 key 前缀
var roleDataSchemaGrantPrefix = map[string]string{
	"master":        "Master",
	"slave":         "Slave",
	"spider_master": "Spider",
}

// addRoleDataSchemaGrant 把扁平化后的 Public.DataSchemaGrant 按角色复制一份为 {Role}.DataSchemaGrant
// 例如 MysqlRole=slave 时增加 "Slave.DataSchemaGrant"；角色不在映射表中时不处理
func addRoleDataSchemaGrant(m map[string]interface{}, mysqlRole string) {
	prefix, ok := roleDataSchemaGrantPrefix[strings.ToLower(mysqlRole)]
	if !ok {
		return
	}
	v, ok := m["Public.DataSchemaGrant"]
	if !ok {
		return
	}
	m[prefix+".DataSchemaGrant"] = v
}
