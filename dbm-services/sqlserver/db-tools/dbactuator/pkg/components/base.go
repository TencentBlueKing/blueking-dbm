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
}
