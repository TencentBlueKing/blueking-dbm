// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package monitoriteminterface

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface/internal"
	"log/slog"

	"github.com/pkg/errors"
)

// ConnectionCollect DB连接对象
type ConnectionCollect struct {
	MySqlDB      *pkg.MySQLMonitorDBH //*sqlx.DB // spider 也用这个
	ProxyDB      *pkg.MySQLMonitorDBH //*sqlx.DB
	ProxyAdminDB *pkg.MySQLMonitorDBH //*sqlx.DB
	CtlDB        *pkg.MySQLMonitorDBH //*sqlx.DB

	itemOptions map[string]ItemOptions
}

// Close 关闭所有连接
func (c *ConnectionCollect) Close() {
	if c.MySqlDB != nil && c.MySqlDB.DB != nil {
		_ = c.MySqlDB.Close()
	}

	if c.ProxyDB != nil && c.ProxyDB.DB != nil {
		_ = c.ProxyDB.Close()
	}

	if c.ProxyAdminDB != nil && c.ProxyAdminDB.DB != nil {
		_ = c.ProxyAdminDB.Close()
	}

	if c.CtlDB != nil && c.CtlDB.DB != nil {
		_ = c.CtlDB.Close()
	}
}

type ItemOptions map[string]interface{}

// InitItemOptions set map  collectorName:options
func (c *ConnectionCollect) InitItemOptions() map[string]ItemOptions {
	opts := make(map[string]ItemOptions)
	for _, opt := range config.ItemsConfig {
		opts[opt.Name] = opt.Options
	}
	c.itemOptions = opts
	return opts
}

// GetCustomOptions return options of collector name
func (c *ConnectionCollect) GetCustomOptions(name string) ItemOptions {
	return c.itemOptions[name]
}

func (o ItemOptions) Get(optionName string, defaultValue interface{}) interface{} {
	if val, ok := o[optionName]; ok {
		return val
	}
	return defaultValue
}
func (o ItemOptions) GetInt(optionName string, defaultValue interface{}) int {
	return o.Get(optionName, defaultValue).(int)
}
func (o ItemOptions) GetBool(optionName string, defaultValue interface{}) bool {
	return o.Get(optionName, defaultValue).(bool)
}
func (o ItemOptions) GetString(optionName string, defaultValue interface{}) string {
	return o.Get(optionName, defaultValue).(string)
}
func (o ItemOptions) GetStringSlice(optionName string, defaultValue interface{}) []string {
	return o.Get(optionName, defaultValue).([]string)
}

// NewConnectionCollect 新建连接
func NewConnectionCollect() (*ConnectionCollect, error) {
	switch config.MonitorConfig.MachineType {
	case "backend", "remote", "single":
		db, err := internal.ConnectMySQL()

		return &ConnectionCollect{MySqlDB: db}, err
	case "proxy":
		pdb, padb, err := internal.ConnectProxy()
		return &ConnectionCollect{
			ProxyDB:      pdb,
			ProxyAdminDB: padb,
		}, err
	case "spider":
		sdb, ctlDB, err := internal.ConnectSpider()
		return &ConnectionCollect{MySqlDB: sdb, CtlDB: ctlDB}, err
	case "mysql_dts_master", "mysql_dts_worker":
		return &ConnectionCollect{}, nil

	default:
		err := errors.Errorf(
			"not support machine type: %s",
			config.MonitorConfig.MachineType,
		)
		slog.Error("new connect", slog.String("error", err.Error()))
		return nil, err
	}
}
