// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package inforeport 信息上报
package inforeport

import (
	"fmt"
	"log/slog"
	"strings"

	"github.com/samber/lo"

	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/inforeport/configreport"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/inforeport/pkgversion"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
)

var name = "info-report"

func init() {
}

type infoReport struct {
	optionMap monitoriteminterface.ItemOptions
	db        *sqlx.DB
}

// Run TODO
func (c *infoReport) Run() (msg string, err error) {
	dbPort := config.MonitorConfig.Port
	if err := configreport.ReportDbbackupConfig(dbPort); err != nil {
		slog.Warn("info-report", slog.String("error", err.Error()))
	}
	if err := configreport.ReportRotatebinlogConfig(0); err != nil {
		slog.Warn("info-report", slog.String("error", err.Error()))
	}
	if err := pkgversion.CollectPkgVersion(); err != nil {
		slog.Warn("info-report", slog.String("error", err.Error()))
	}
	if err := reportMycnfConfig(c); err != nil {
		slog.Warn("info-report", slog.String("error", err.Error()))
	}
	return "", nil
}

// Name TODO
func (c *infoReport) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	opts := cc.GetCustomOptions(name) // ItemOptions is map[string]interface{}
	var itemObj = infoReport{}
	itemObj.db = cc.MySqlDB
	itemObj.optionMap = opts

	return &itemObj
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}

// reportMycnfConfig 信息上报到 ~/dbareport/mixed/mycnf_config_{port}.log
func reportMycnfConfig(c *infoReport) error {
	report, err := configreport.GetMixedReport(fmt.Sprintf("mycnf_config_%d.log", config.MonitorConfig.Port))
	if err != nil {
		return err
	}
	// 采集哪些 mysqld my.cnf 配置项
	items := c.optionMap.GetString("mysqld_config", strings.Join(mysql.MycnfCloneItemsDefault, ","))
	spiderItems := []string{
		"version",
		"spider_auto_increment_step",
		"spider_net_read_timeout",
		"spider_net_write_timeout",
		"spider_quick_mode",
		"spider_bgs_mode",
		"default_storage_engine",
		"collation_server",
		"log_bin", "binlog_format", "binlog_rows_query_log_events", "log_bin_compress",
		"binlog_group_commit_sync_delay", "binlog_group_commit_sync_no_delay_count",
		"gtid_mode",
		"performance_schema",
		"innodb_io_capacity", "innodb_read_io_threads", "innodb_write_io_threads",
		"thread_cache_size", "thread_handling",
		"innodb_buffer_pool_size", "join_buffer_size", "sort_buffer_size", "slave_skip_errors",
		"tc_admin", "dbm_allow_standalone_primary", "ddl_execute_by_ctl",
	}
	mergedItems := lo.Uniq[string](append(strings.Split(items, ","), spiderItems...))
	res, err := configreport.QueryMycnfConfig(mergedItems, c.db)
	if err != nil {
		return err
	}
	res["port"] = config.MonitorConfig.Port
	res["ip"] = config.MonitorConfig.Ip
	res["cluster_domain"] = config.MonitorConfig.ImmuteDomain
	event := configreport.NewDynamicEvent("mycnf_config", "tendbha", 1)
	event.SetPayload(res)
	report.Println(event)
	return nil
}
