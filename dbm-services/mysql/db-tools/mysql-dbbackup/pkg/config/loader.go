// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

// LogicalLoad the config of logical loading
type LogicalLoad struct {
	MysqlLoadDir  string `ini:"MysqlLoadDir" validate:"required"`
	IndexFilePath string `ini:"IndexFilePath" validate:"required,file"`
	MysqlHost     string `ini:"MysqlHost"`
	MysqlPort     int    `ini:"MysqlPort"`
	MysqlUser     string `ini:"MysqlUser" validate:"required"`
	MysqlPasswd   string `ini:"MysqlPasswd"`
	MysqlCharset  string `ini:"MysqlCharset"`
	EnableBinlog  bool   `ini:"EnableBinlog"`
	// InitCommand set global xxx=y;
	// for myloader, no native --init-command option, will set variables to --defaults-file
	// for mysqldump, will append --init-command to mysql cli
	InitCommand string `json:"InitCommand"`

	// Threads logical loader concurrency for myloader
	Threads int `ini:"Threads"`
	// SchemaOnly import schema,trigger,func,proc (--no-data), for myloader
	//  if you want only table schema, use ExtraOpt = -skip-triggers --skip-post
	//  mydumper doest not support data only currently, you should backup only data for your purpose
	SchemaOnly bool   `ini:"SchemaOnly"`
	ExtraOpt   string `ini:"ExtraOpt"` // other myloader options string to be appended
	// DBListDropIfExists will run drop database if exists db_xxx before load data. comma separated
	DBListDropIfExists string `ini:"DBListDropIfExists"`
	// CreateTableIfNotExists true will add --append-if-not-exist for myloader
	CreateTableIfNotExists bool `ini:"CreateTableIfNotExists"`

	// filterType form, regex, tables
	TableFilter `ini:"LogicalLoad" mapstructure:",squash"` // viper squash is used to simplify code
}

// LogicalLoadMysqldump the config of logical loading with mysql
type LogicalLoadMysqldump struct {
	BinPath  string `ini:"BinPath"`  // the binary path of mysql
	ExtraOpt string `ini:"ExtraOpt"` // other mysql options string to be appended(we use mysql to load backup)
}

// PhysicalLoad the config of physical loading
// works for innodb, rocksdb, tokudb
type PhysicalLoad struct {
	MysqlLoadDir  string `ini:"MysqlLoadDir" validate:"required"`
	IndexFilePath string `ini:"IndexFilePath" validate:"required,file"`

	// DefaultsFile the target instance's my.cnf, not from backup files
	DefaultsFile string `ini:"DefaultsFile" validate:"required"`
	Threads      int    `ini:"Threads"`
	CopyBack     bool   `ini:"CopyBack"` // use copy-back or move-back
	ExtraOpt     string `ini:"ExtraOpt"` // other xtrabackup recover options string to be appended
}
