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
	"dbm-services/riak/db-tools/riak-monitor/pkg/itemscollect/checkload"
	"dbm-services/riak/db-tools/riak-monitor/pkg/itemscollect/checkringstatus"
	"dbm-services/riak/db-tools/riak-monitor/pkg/itemscollect/connections"
	"dbm-services/riak/db-tools/riak-monitor/pkg/itemscollect/riakconsolelog"
	mi "dbm-services/riak/db-tools/riak-monitor/pkg/monitoriteminterface"
	"fmt"

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
	_ = registerItemConstructor(riakconsolelog.RegisterRiakErrNotice())
	_ = registerItemConstructor(checkringstatus.RegisterCheckRingStatus())
	_ = registerItemConstructor(checkload.RegisterCheckLoadHealth())
	_ = registerItemConstructor(connections.RegisterConnections())
}
