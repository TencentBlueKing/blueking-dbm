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

	"github.com/pkg/errors"

	actorCst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

// optionKeySource dbbackup.options 的 key 及其来源（扁平化后 payload 中的 key）
type optionKeySource struct {
	key       string
	dbbackup  string // dbbackup.ini 中的 key，空表示不从 dbbackup.ini 取
	rotateBin string // rotatebinlog main.yaml 中的 key，空表示不从 rotatebinlog 取
}

// dbbackupOptionKeys 与 dbactuator dbbackup.BackupOptions 对应
// 这些参数由 gen_config 渲染进 dbbackup.ini / rotatebinlog main.yaml，这里反向取回
var dbbackupOptionKeys = []optionKeySource{
	{key: "BackupType", dbbackup: "Public.BackupType"},
	{key: "CrontabTime", dbbackup: "Schedule.CronTime"},
	{key: "Master.DataSchemaGrant", dbbackup: "Master.DataSchemaGrant"},
	{key: "Slave.DataSchemaGrant", dbbackup: "Slave.DataSchemaGrant"},
	{key: "Readonly.DataSchemaGrant", dbbackup: "Readonly.DataSchemaGrant"},
	{key: "Spider.DataSchemaGrant", dbbackup: "Spider.DataSchemaGrant"},
	{key: "EnableBackupClient", dbbackup: "EnableBackupClient", rotateBin: "EnableBackupClient"},
}

// ReportDbbackupOptions 按端口上报 dbbackup.options（备份控制参数）
// 本机没有 dbbackup.options 文件，值从 dbbackup.{port}.ini 与 rotatebinlog main.yaml 中取回
// 同一个 key 在多个来源都有值时，去重后用 "," 拼接（例如两边 EnableBackupClient 不一致时为 "auto,yes"）
// dbbackup.ini 不存在时删除 local_config 中对应的行
func ReportDbbackupOptions(dbPort int, db *pkg.MySQLMonitorDBH) error {
	dbbackupFile := filepath.Join(actorCst.DbbackupGoInstallPath, fmt.Sprintf("dbbackup.%d.ini", dbPort))
	rotateFile := filepath.Join(actorCst.MysqlRotateBinlogInstallPath, "main.yaml")
	cfg := &ModelLocalConfig{
		Host:      config.MonitorConfig.Ip,
		Port:      dbPort,
		ConfType:  "backup",
		ConfFile:  "dbbackup.options",
		ConfigKey: "",
	}

	fi, err := os.Stat(dbbackupFile)
	if err != nil {
		if os.IsNotExist(err) {
			return DeleteLocalConfig(db, cfg)
		}
		return errors.WithMessagef(err, "stat %s", dbbackupFile)
	}
	// 来源有两个文件，用 mtime 之和作为 conf_mtime：任一文件变化都会使其改变
	// （取最大值不行：较旧的那个文件被修改后可能仍小于另一个文件的 mtime）
	cfg.ConfMtime = fi.ModTime().Unix()
	rotateExists := false
	if rfi, err := os.Stat(rotateFile); err == nil {
		rotateExists = true
		cfg.ConfMtime += rfi.ModTime().Unix()
	} else if !os.IsNotExist(err) {
		return errors.WithMessagef(err, "stat %s", rotateFile)
	}

	needWrite, err := NeedWriteLocalConfig(db, cfg)
	if err != nil {
		return err
	}
	if !needWrite {
		slog.Debug("skip dbbackup options report, no change", slog.Int("port", dbPort))
		return nil
	}

	dbbackupPayload, err := buildDbbackupPayload(dbbackupFile)
	if err != nil {
		return err
	}
	var rotatePayload map[string]interface{}
	if rotateExists {
		if rotatePayload, err = buildRotatebinlogPayload(rotateFile); err != nil {
			return err
		}
	}

	payload := buildDbbackupOptions(dbbackupPayload, rotatePayload)
	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	report, err := GetMixedReport(fmt.Sprintf("dbbackup_options_%d.log", dbPort))
	if err != nil {
		return err
	}
	event := NewDynamicEvent("dbbackup_options", "tendbha", 1)
	event.SetPayload(payload)
	report.Println(event)

	cfg.ConfigValue = string(bodyBytes)
	cfg.ClusterDomain = config.MonitorConfig.ImmuteDomain
	return ReplaceLocalConfig(db, cfg)
}

// buildDbbackupOptions 按 dbbackupOptionKeys 从两个来源取值，同名 key 的多个值去重后用 "," 拼接
// 来源中都不存在的 key 不输出；空字符串不参与拼接
func buildDbbackupOptions(dbbackupPayload, rotatePayload map[string]interface{}) map[string]interface{} {
	res := make(map[string]interface{})
	for _, ks := range dbbackupOptionKeys {
		var values []string
		found := false
		collect := func(src map[string]interface{}, k string) {
			if src == nil || k == "" {
				return
			}
			v, ok := src[k]
			if !ok || v == nil {
				return
			}
			found = true
			s := fmt.Sprintf("%v", v)
			if s == "" {
				return
			}
			for _, e := range values {
				if e == s {
					return
				}
			}
			values = append(values, s)
		}
		collect(dbbackupPayload, ks.dbbackup)
		collect(rotatePayload, ks.rotateBin)
		if found {
			res[ks.key] = strings.Join(values, ",")
		}
	}
	return res
}
