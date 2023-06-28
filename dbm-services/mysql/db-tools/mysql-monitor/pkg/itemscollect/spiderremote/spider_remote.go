// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package spiderremote

import (
	"context"
	"encoding/json"
	"fmt"
	"hash/crc32"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"
)

/*
检查spider的mysql.servers表，要求
1. 各分片的remote ip一致
2. 上报remote ip
*/

var name = "spider-remote"

type spiderRemoteCheck struct {
	db *sqlx.DB
}

func (c *spiderRemoteCheck) Run() (msg string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var res []struct {
		ServerName string `db:"Server_name"`
		Host       string `db:"Host"`
		Port       int    `db:"Port"`
	}
	err = c.db.SelectContext(
		ctx,
		&res,
		`SELECT Server_name, Host, Port FROM mysql.servers WHERE Wrapper = 'mysql' ORDER BY Server_name`)
	if err != nil {
		return "", errors.Wrap(err, "query mysql.servers")
	}

	if len(res) <= 0 {
		msg = fmt.Sprintf("remote routine not found in mysql.servers")
		return msg, nil
	}

	b, err := json.Marshal(res)
	if err != nil {
		slog.Error("spider remote marshal res", err, slog.Any("res", res))
		return "", err
	}

	remoteCrc := crc32.ChecksumIEEE(b)
	slog.Info("spider remote",
		slog.String("remote info", string(b)),
		slog.Int64("remote crc", int64(remoteCrc)))

	utils.SendMonitorMetrics(
		"spider_remote_ip",
		int64(remoteCrc),
		nil,
	)

	return msg, nil
}

func (c *spiderRemoteCheck) Name() string {
	return name
}

func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &spiderRemoteCheck{db: cc.MySqlDB}
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
