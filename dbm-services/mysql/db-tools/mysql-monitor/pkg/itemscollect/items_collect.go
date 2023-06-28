// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package itemscollect 监控项
package itemscollect

import (
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/characterconsistency"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/definer"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/engine"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/ext3check"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/ibdstatistic"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/masterslaveheartbeat"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/mysqlconfigdiff"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/mysqlconnlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/mysqlerrlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/mysqlprocesslist"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/proxybackend"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/proxyuserlist"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/rotateslowlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/slavestatus"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/spiderremote"
	mi "dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"golang.org/x/exp/slog"
)

var registeredItemConstructor map[string]func(*mi.ConnectionCollect) mi.MonitorItemInterface

func registerItemConstructor(
	name string, f func(*mi.ConnectionCollect) mi.MonitorItemInterface,
) error {
	if _, ok := registeredItemConstructor[name]; ok {
		err := fmt.Errorf("%s already registered", name)
		slog.Error("register item creator", err)
		return err
	}
	registeredItemConstructor[name] = f
	return nil
}

// RegisteredItemConstructor 返回注册列表
func RegisteredItemConstructor() map[string]func(*mi.ConnectionCollect) mi.MonitorItemInterface {
	return registeredItemConstructor
}

func init() {
	registeredItemConstructor = make(map[string]func(*mi.ConnectionCollect) mi.MonitorItemInterface)
	/*
		注册监控项
	*/
	_ = registerItemConstructor(characterconsistency.Register())
	_ = registerItemConstructor(definer.RegisterCheckTriggerDefiner())
	_ = registerItemConstructor(definer.RegisterCheckViewDefiner())
	_ = registerItemConstructor(definer.RegisterCheckRoutineDefiner())
	_ = registerItemConstructor(engine.Register())
	_ = registerItemConstructor(ext3check.Register())
	_ = registerItemConstructor(masterslaveheartbeat.Register())
	_ = registerItemConstructor(slavestatus.RegisterSlaveStatusChecker())
	_ = registerItemConstructor(mysqlerrlog.RegisterMySQLErrNotice())
	_ = registerItemConstructor(mysqlerrlog.RegisterMySQLErrCritical())
	_ = registerItemConstructor(mysqlerrlog.RegisterSpiderErrNotice())
	_ = registerItemConstructor(mysqlerrlog.RegisterSpiderErrWarn())
	_ = registerItemConstructor(mysqlerrlog.RegisterSpiderErrCritical())
	_ = registerItemConstructor(mysqlprocesslist.RegisterMySQLLock())
	_ = registerItemConstructor(mysqlprocesslist.RegisterMySQLInject())
	_ = registerItemConstructor(rotateslowlog.RegisterRotateSlowLog())
	_ = registerItemConstructor(mysqlconnlog.RegisterMySQLConnLogSize())
	_ = registerItemConstructor(mysqlconnlog.RegisterMySQLConnLogRotate())
	_ = registerItemConstructor(mysqlconnlog.RegisterMySQLConnLogReport())
	_ = registerItemConstructor(mysqlconfigdiff.Register())
	_ = registerItemConstructor(proxyuserlist.Register())
	_ = registerItemConstructor(proxybackend.Register())
	_ = registerItemConstructor(ibdstatistic.Register())
	_ = registerItemConstructor(slavestatus.RegisterCtlReplicateChecker())
	_ = registerItemConstructor(spiderremote.Register())
}
