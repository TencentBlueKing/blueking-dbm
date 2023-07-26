// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package riakconsolelog

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/monitoriteminterface"
)

var nameRiakErrNotice = "riak-err-notice"

// Checker TODO
type Checker struct {
	name string
	f    func() (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	return c.f()
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewRiakErrNotice TODO
func NewRiakErrNotice(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		name: nameRiakErrNotice,
		f:    riakNotice,
	}
}

// RegisterRiakErrNotice TODO
func RegisterRiakErrNotice() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return nameRiakErrNotice, NewRiakErrNotice
}
