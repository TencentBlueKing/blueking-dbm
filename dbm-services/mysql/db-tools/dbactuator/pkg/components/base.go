/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package components

// BaseInputParam TODO
type BaseInputParam struct {
	GeneralParam *GeneralParam `json:"general"`
	ExtendParam  interface{}   `json:"extend"`
}

// GeneralParam TODO
type GeneralParam struct {
	RuntimeAccountParam RuntimeAccountParam `json:"runtime_account"`
	RuntimeExtend       RuntimeExtend       `json:"runtime_extend"`
}

// RuntimeExtend TODO
type RuntimeExtend struct {
	MySQLSysUsers []string `json:"mysql_sys_users"`
}

// RuntimeAccountParam TODO
type RuntimeAccountParam struct {
	MySQLAccountParam
	ProxyAccountParam
	TdbctlAccoutParam
	TBinlogDumperAccoutParam
}

// GetAllSysAccount TODO
func (g *GeneralParam) GetAllSysAccount() (accounts []string) {
	accounts = g.RuntimeExtend.MySQLSysUsers
	accounts = append(accounts, g.RuntimeAccountParam.AdminUser)
	accounts = append(accounts, g.RuntimeAccountParam.DbBackupUser)
	accounts = append(accounts, g.RuntimeAccountParam.MonitorAccessAllUser)
	accounts = append(accounts, g.RuntimeAccountParam.MonitorUser)
	accounts = append(accounts, g.RuntimeAccountParam.ReplUser)
	accounts = append(accounts, g.RuntimeAccountParam.YwUser)
	accounts = append(accounts, g.RuntimeAccountParam.TdbctlUser)
	return
}

// GetAccountRepl TODO
func GetAccountRepl(g *GeneralParam) MySQLReplAccount {
	Repl := MySQLReplAccount{}
	switch {
	case g == nil:
		return Repl
	case g.RuntimeAccountParam == RuntimeAccountParam{}:
		return Repl
	case g.RuntimeAccountParam.MySQLAccountParam == MySQLAccountParam{}:
		return Repl
	default:
		return g.RuntimeAccountParam.MySQLReplAccount
	}
}
