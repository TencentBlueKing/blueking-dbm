// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package monitoriteminterface

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

// ConnectionCollect DB连接对象
type ConnectionCollect struct {
	MySqlDB      *sqlx.DB // spider 也用这个
	ProxyDB      *sqlx.DB
	ProxyAdminDB *sqlx.DB
	CtlDB        *sqlx.DB
}

// Close 关闭所有连接
func (c *ConnectionCollect) Close() {
	if c.MySqlDB != nil {
		_ = c.MySqlDB.Close()
	}

	if c.ProxyDB != nil {
		_ = c.ProxyDB.Close()
	}

	if c.ProxyAdminDB != nil {
		_ = c.ProxyAdminDB.Close()
	}

	if c.CtlDB != nil {
		_ = c.CtlDB.Close()
	}
}

// NewConnectionCollect 新建连接
func NewConnectionCollect() (*ConnectionCollect, error) {
	switch config.MonitorConfig.MachineType {
	case "backend", "remote", "single":
		db, err := connectDB(
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			config.MonitorConfig.Auth.Mysql,
		)
		if err != nil {
			slog.Error(
				fmt.Sprintf("connect %s", config.MonitorConfig.MachineType),
				slog.String("error", err.Error()),
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", config.MonitorConfig.Port),
			)
			return nil, err
		}
		return &ConnectionCollect{MySqlDB: db}, nil
	case "proxy":
		db1, err := connectDB(
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			config.MonitorConfig.Auth.Proxy,
		)
		if err != nil {
			slog.Error(
				"connect proxy",
				slog.String("error", err.Error()),
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", config.MonitorConfig.Port),
			)
			return nil, err
		}

		adminPort := config.MonitorConfig.Port + 1000
		db2, err := connectDB(
			config.MonitorConfig.Ip,
			adminPort,
			config.MonitorConfig.Auth.ProxyAdmin,
		)
		if err != nil {
			var merr *mysql.MySQLError
			if errors.As(err, &merr) {
				if merr.Number == 1105 {
					// 连接 proxy 管理端肯定在这里返回
					return &ConnectionCollect{ProxyDB: db1, ProxyAdminDB: db2}, nil
				}
			}
			slog.Error(
				"connect proxy admin",
				slog.String("error", err.Error()),
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", adminPort),
			)
			return nil, err
		}
		// 这里其实永远到不了, 因为 mysql 协议连接 proxy 管理端必然 err!=nil
		return &ConnectionCollect{ProxyDB: db1, ProxyAdminDB: db2}, nil
	case "spider":
		db1, err := connectDB(
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			config.MonitorConfig.Auth.Mysql,
		)
		if err != nil {
			slog.Error(
				"connect spider",
				slog.String("error", err.Error()),
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", config.MonitorConfig.Port),
			)
			return nil, err
		}

		// spider_slave 不建立到中控的连接
		// 所以要小心
		var db2 *sqlx.DB
		if *config.MonitorConfig.Role == "spider_master" {
			ctlPort := config.MonitorConfig.Port + 1000
			db2, err = connectDB(
				config.MonitorConfig.Ip,
				ctlPort,
				config.MonitorConfig.Auth.Mysql,
			)
			if err != nil {
				slog.Error(
					"connect ctl",
					slog.String("error", err.Error()),
					slog.String("ip", config.MonitorConfig.Ip),
					slog.Int("port", ctlPort),
				)
				return nil, err
			}
		}

		return &ConnectionCollect{MySqlDB: db1, CtlDB: db2}, nil
	default:
		err := errors.Errorf(
			"not support machine type: %s",
			config.MonitorConfig.MachineType,
		)
		slog.Error("new connect", slog.String("error", err.Error()))
		return nil, err
	}
}

func connectDB(ip string, port int, ca *config.ConnectAuth) (*sqlx.DB, error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	return sqlx.ConnectContext(
		ctx,
		"mysql", fmt.Sprintf(
			"%s:%s@tcp(%s:%d)/%s?parseTime=true&loc=%s&timeout=%s",
			ca.User, ca.Password, ip, port,
			"",
			time.Local.String(),
			config.MonitorConfig.InteractTimeout,
		),
	)
}
