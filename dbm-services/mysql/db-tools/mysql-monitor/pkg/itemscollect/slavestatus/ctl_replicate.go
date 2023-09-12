// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package slavestatus

import (
	"context"
	"fmt"

	"golang.org/x/exp/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

var ctlReplicateName = "ctl-replicate"

type ctlReplicateChecker struct {
	slaveStatusChecker
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
	return "", nil
}

func (c *ctlReplicateChecker) isPrimary() (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var getPrimaryRes []struct {
		ServerName string `db:"SERVER_NAME"`
		Host       string `db:"HOST"`
		Port       string `db:"PORT"`
		IsThis     int    `db:"IS_THIS_SERVER"`
	}

	err := c.db.SelectContext(ctx, &getPrimaryRes, `TDBCTL GET PRIMARY`)
	if err != nil {
		slog.Error("TDBCTL GET PRIMARY", err)
		return false, err
	}

	//var tcIsPrimary sql.NullInt32
	//err := c.db.GetContext(ctx, &tcIsPrimary, `SELECT @@tc_is_primary`)
	//if err != nil {
	//	slog.Error("select @@tc_is_primary", err)
	//	return false, err
	//}
	//
	//if !tcIsPrimary.Valid {
	//	err := errors.Errorf("invalide tc_is_primary: %v", tcIsPrimary)
	//	slog.Error("select @@tc_is_primary", err)
	//	return false, err
	//}

	return getPrimaryRes[0].IsThis == 1, nil
}

// Name 监控项名
func (c *ctlReplicateChecker) Name() string {
	return ctlReplicateName
}

// NewCtlReplicateChecker 新建监控项实例
func NewCtlReplicateChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &ctlReplicateChecker{slaveStatusChecker{
		db:          cc.CtlDB,
		slaveStatus: make(map[string]interface{}),
	}}
}

// RegisterCtlReplicateChecker 注册监控项
func RegisterCtlReplicateChecker() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return ctlReplicateName, NewCtlReplicateChecker
}
