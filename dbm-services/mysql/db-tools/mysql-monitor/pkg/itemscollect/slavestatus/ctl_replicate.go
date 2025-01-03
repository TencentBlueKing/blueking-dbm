// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package slavestatus

import (
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

var ctlReplicateName = "ctl-replicate"

type ctlReplicateChecker struct {
	slaveStatusChecker
	primary *getPrimaryRes
}

type getPrimaryRes struct {
	ServerName   string `db:"SERVER_NAME"`
	Host         string `db:"HOST"`
	Port         uint32 `db:"PORT"`
	IsThisServer uint32 `db:"IS_THIS_SERVER"`
}

// Run 运行
func (c *ctlReplicateChecker) Run() (msg string, err error) {
	isPrimary, err := c.isPrimary()
	if err != nil {
		return "", err
	}

	if isPrimary {
		return "", nil
	}

	err = c.fetchSlaveStatus()
	if err != nil {
		return "", err
	}

	if c.slaveStatus == nil || len(c.slaveStatus) == 0 {
		return "empty slave status", nil
	}

	if !c.isOk() {
		slaveErr, err := c.collectError()
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("IO/SQL thread not running: %s", slaveErr), nil

	}
	slog.Info(
		"tdbctl primary is master",
		slog.String("primary", c.primary.Host),
		slog.String("master", c.masterHost()),
	)
	if c.masterHost() != c.primary.Host {
		err = fmt.Errorf(
			"tdbctl slave's master host [%s] != primary host [%s]",
			c.masterHost(), c.primary.Host,
		)
		slog.Error("tdbctl primary is master", slog.String("err", err.Error()))
		return "", err
	}
	return "", nil
}

func (c *ctlReplicateChecker) isPrimary() (bool, error) {
	res := getPrimaryRes{}

	err := c.db.QueryRowx(`TDBCTL GET PRIMARY`).StructScan(&res)
	if err != nil {
		slog.Error("TDBCTL GET PRIMARY", slog.String("error", err.Error()))
		return false, err
	}
	c.primary = &res

	return res.IsThisServer == 1, nil
}

// Name 监控项名
func (c *ctlReplicateChecker) Name() string {
	return ctlReplicateName
}

// NewCtlReplicateChecker 新建监控项实例
func NewCtlReplicateChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &ctlReplicateChecker{
		slaveStatusChecker{
			db:          cc.CtlDB,
			slaveStatus: make(map[string]interface{}),
		},
		nil,
	}
}

// RegisterCtlReplicateChecker 注册监控项
func RegisterCtlReplicateChecker() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return ctlReplicateName, NewCtlReplicateChecker
}
