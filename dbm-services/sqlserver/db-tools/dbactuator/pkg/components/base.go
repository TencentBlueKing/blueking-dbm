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

import "fmt"

// BaseInputParam TODO
type BaseInputParam struct {
	GeneralParam *GeneralParam `json:"general"`
	ExtendParam  interface{}   `json:"extend"`
}

// GeneralParam TODO
type GeneralParam struct {
	RuntimeAccountParam RuntimeAccountParam `json:"runtime_account"`
	// more Runtime Struct
}

// RuntimeAccountParam TODO
type RuntimeAccountParam struct {
	// mssql 账户
	OSMssqlUser string `json:"mssql_user,omitempty"`
	// mssql 密码
	OSMssqlPwd string `json:"mssql_pwd,omitempty"`
	// sa 账户
	SAUser string `json:"sa_user,omitempty"`
	// sa 密码
	SAPwd string `json:"sa_pwd,omitempty"`
	// sqlserver 账户
	SQLServerUser string `json:"sqlserver_user,omitempty"`
	// sqlserver 密码
	SQLServerPwd string `json:"sqlserver_pwd,omitempty"`
	// mssql_exporter 账号
	MssqlExporterUser string `json:"exporter_user,omitempty"`
	// mssql_exporter 密码
	MssqlExporterPwd string `json:"exporter_pwd,omitempty"`
	// admin 账号
	MssqlAdminUser string `json:"mssql_admin_user,omitempty"`
	// admin 密码
	MssqlAdminPwd string `json:"mssql_admin_pwd,omitempty"`
	// drs 账号
	DRSUser string `json:"drs_user,omitempty"`
	// drs 密码
	DRSPwd string `json:"drs_pwd,omitempty"`
	// 业务数据只读 账号
	DRSDataReadUser string `json:"drs_data_read_user,omitempty"`
	// 业务数据只读 密码
	DRSDataReadPwd string `json:"drs_data_read_pwd,omitempty"`
	// 系统只读 账号
	DRSSysReadUser string `json:"drs_sys_read_user,omitempty"`
	// 系统只读 密码
	DRSSysReadPwd string `json:"drs_sys_read_pwd,omitempty"`
	// DBHA 账号
	DBHAUser string `json:"DBHA_user,omitempty"`
	// DBHA 密码
	DBHAPwd string `json:"DBHA_pwd,omitempty"`
}

// String 实现 fmt.Stringer，对所有 `*Pwd` 字段做脱敏（非空 → "***"），账号字段保持明文。
//
// 目的：`Deserialize` 及其他地方以 `%v` / `%+v` 打印 GeneralParam 时，避免把解密后的明文密码
// 落到日志文件。凡是新增以 `Pwd` 结尾的字段，请务必在此处一并追加脱敏。
func (r RuntimeAccountParam) String() string {
	mask := func(s string) string {
		if s == "" {
			return ""
		}
		return "***"
	}
	return fmt.Sprintf(
		"{OSMssqlUser:%s OSMssqlPwd:%s SAUser:%s SAPwd:%s "+
			"SQLServerUser:%s SQLServerPwd:%s "+
			"MssqlExporterUser:%s MssqlExporterPwd:%s "+
			"MssqlAdminUser:%s MssqlAdminPwd:%s "+
			"DRSUser:%s DRSPwd:%s "+
			"DRSDataReadUser:%s DRSDataReadPwd:%s "+
			"DRSSysReadUser:%s DRSSysReadPwd:%s "+
			"DBHAUser:%s DBHAPwd:%s}",
		r.OSMssqlUser, mask(r.OSMssqlPwd),
		r.SAUser, mask(r.SAPwd),
		r.SQLServerUser, mask(r.SQLServerPwd),
		r.MssqlExporterUser, mask(r.MssqlExporterPwd),
		r.MssqlAdminUser, mask(r.MssqlAdminPwd),
		r.DRSUser, mask(r.DRSPwd),
		r.DRSDataReadUser, mask(r.DRSDataReadPwd),
		r.DRSSysReadUser, mask(r.DRSSysReadPwd),
		r.DBHAUser, mask(r.DBHAPwd),
	)
}
