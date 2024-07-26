// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language \governing permissions and limitations under the License.

package config

// LogicalBackup the config of logical backup
// data or schema is controlled by Public.DataSchemaGrant
type LogicalBackup struct {
	Threads int `ini:"Threads"`
	// ChunkFilesize split tables into chunks of this output file size. This value is in MB
	ChunkFilesize uint64 `ini:"ChunkFilesize"`
	// DisableCompress disable zstd compress. compress is enable by default
	DisableCompress bool   `ini:"DisableCompress"`
	FlushRetryCount int    `ini:"FlushRetryCount"`
	DefaultsFile    string `ini:"DefaultsFile"`
	// ExtraOpt for mydumper
	ExtraOpt string `ini:"ExtraOpt"` // other mydumper options string to be appended
	// InsertMode insert | insert_ignore | replace, default '' means insert
	InsertMode string `ini:"InsertMode"`

	// the following options is used when Public.DataSchemaGrant is empty

	// NoSchemas Do not dump table schemas with the data and triggers
	NoSchemas bool `ini:"NoSchemas"`
	// NoData Do not dump table data
	NoData bool `ini:"NoData"`
	// NoView Do not dump VIEWs
	//NoViews bool `ini:"NoViews"`
	// Triggers Dump triggers. By default, it do not dump triggers
	Triggers bool `ini:"Triggers"`
	// Events Dump events. By default, it do not dump events
	Events bool `ini:"Events"`
	// Routines Dump stored procedures and functions. By default, it do not dump stored procedures nor functions
	Routines bool `ini:"Routines"`

	// UseMysqldump yes means used, no means disabled, auto depends on glibc version. The default value is no
	UseMysqldump string `ini:"UseMysqldump"`

	TableFilter `ini:"LogicalBackup" mapstructure:",squash"`
}

// LogicalBackupMysqldump the config of logical backup with mysqldump
type LogicalBackupMysqldump struct {
	BinPath string `ini:"BinPath"` // the binary path of mysqldump
	// ExtraOpt for mysqldump
	ExtraOpt string `ini:"ExtraOpt"` // other mysqldump options string to be appended
}
