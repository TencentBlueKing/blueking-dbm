// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package configreport

import (
	"fmt"
	"log/slog"
	"os"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

// ReportMonitorItemsConfig 按端口上报 mysql-monitor 监控项配置 items-config_{port}.yaml
// 整个文件转成 {"监控项名": 监控项配置} 的 JSON 字典存一行（config_key 为空）
// 仅当配置文件 mtime 变化或距上次写入超过 24 小时时才写入 local_config 和上报日志
// 配置文件不存在时删除 local_config 中对应的行
func ReportMonitorItemsConfig(dbPort int, db *pkg.MySQLMonitorDBH) error {
	confFile := config.MonitorConfig.ItemsConfigFile
	cfg := &ModelLocalConfig{
		Host:      config.MonitorConfig.Ip,
		Port:      dbPort,
		ConfType:  "mysql_monitor",
		ConfFile:  "items-config.yaml",
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
		slog.Debug("skip mysql-monitor config report, no change", slog.String("file", confFile))
		return nil
	}

	// 解析方式与 config.LoadMonitorItemsConfig 一致，但不改动全局 config.ItemsConfig
	content, err := os.ReadFile(confFile)
	if err != nil {
		return errors.WithMessagef(err, "read %s", confFile)
	}
	var items []*config.MonitorItem
	if err = yaml.UnmarshalStrict(content, &items); err != nil {
		return errors.WithMessagef(err, "parse %s", confFile)
	}
	// 转成以监控项名为 key 的字典，value 与 dbconfig 的 conf_value 结构一致（保留 name 字段）
	itemsMap := make(map[string]*config.MonitorItem, len(items))
	for _, item := range items {
		if item == nil || item.Name == "" {
			continue
		}
		// yaml.v2 把嵌套 map 解析成 map[interface{}]interface{}，json 无法序列化，先转换
		item.Options = normalizeYamlMap(item.Options)
		itemsMap[item.Name] = item // 同名监控项以后出现的为准
	}

	payload, body, err := MaskedJSONPayload(itemsMap)
	if err != nil {
		return err
	}
	report, err := GetMixedReport(fmt.Sprintf("mysql_monitor_config_%d.log", dbPort))
	if err != nil {
		return err
	}
	event := NewDynamicEvent("mysql_monitor_config", "tendbha", 1)
	event.SetPayload(payload)
	report.Println(event)

	cfg.ConfigValue = body
	cfg.ClusterDomain = config.MonitorConfig.ImmuteDomain
	return ReplaceLocalConfig(db, cfg)
}

// normalizeYamlMap 递归把 yaml.v2 解析出的 map[interface{}]interface{} 转为 map[string]interface{}
func normalizeYamlMap(m map[string]interface{}) map[string]interface{} {
	if m == nil {
		return nil
	}
	for k, v := range m {
		m[k] = normalizeYamlValue(v)
	}
	return m
}

func normalizeYamlValue(v interface{}) interface{} {
	switch t := v.(type) {
	case map[interface{}]interface{}:
		res := make(map[string]interface{}, len(t))
		for k, val := range t {
			res[fmt.Sprintf("%v", k)] = normalizeYamlValue(val)
		}
		return res
	case map[string]interface{}:
		return normalizeYamlMap(t)
	case []interface{}:
		for i := range t {
			t[i] = normalizeYamlValue(t[i])
		}
		return t
	default:
		return v
	}
}
