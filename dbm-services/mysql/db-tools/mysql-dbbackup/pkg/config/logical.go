// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language \governing permissions and limitations under the License.

package config

import (
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

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

	// 三种类型的过滤方式，互斥
	// 1. regex 正则过滤，优先用于 mydumper
	// 2. databases, tables, exclude-databases, exclude-tables, 精确名字，通用，可用于 mydumper, mysqldump
	// 3. tables-list, 精确 db 或者 db.table
	// Regex mydumper regex format
	Regex string `ini:"Regex"`

	Databases        string `ini:"Databases"`
	Tables           string `ini:"Tables"`
	ExcludeDatabases string `ini:"ExcludeDatabases"`
	ExcludeTables    string `ini:"ExcludeTables"`

	// TablesList db1.table1 format
	TablesList string `ini:"TablesList"`
	// filterType form, regex, tables
	filterType FilterType
	// 是否备份实例所有业务db
	isFullData bool
}

// LogicalLoad the config of logical loading
type LogicalLoad struct {
	MysqlHost     string `ini:"MysqlHost"`
	MysqlPort     int    `ini:"MysqlPort"`
	MysqlUser     string `ini:"MysqlUser"`
	MysqlPasswd   string `ini:"MysqlPasswd"`
	MysqlCharset  string `ini:"MysqlCharset"`
	MysqlLoadDir  string `ini:"MysqlLoadDir"`
	EnableBinlog  bool   `ini:"EnableBinlog"`
	IndexFilePath string `ini:"IndexFilePath" validate:"required"`

	// Threads logical loader concurrency for myloader
	Threads int `ini:"Threads"`
	// Regex for myloader
	Regex string `ini:"Regex"`
	// SchemaOnly import schema,trigger,func,proc (--no-data), for myloader
	//  if you want only table schema, use ExtraOpt = -skip-triggers --skip-post
	//  mydumper doest not support data only currently, you should backup only data for your purpose
	SchemaOnly bool   `ini:"SchemaOnly"`
	ExtraOpt   string `ini:"ExtraOpt"` // other myloader options string to be appended
	// DBListDropIfExists will run drop database if exists db_xxx before load data. comma separated
	DBListDropIfExists string `ini:"DBListDropIfExists"`
	// CreateTableIfNotExists true will add --append-if-not-exist for myloader
	CreateTableIfNotExists bool `ini:"CreateTableIfNotExists"`
}

// LogicalBackupMysqldump the config of logical backup with mysqldump
type LogicalBackupMysqldump struct {
	BinPath string `ini:"BinPath"` // the binary path of mysqldump
	// ExtraOpt for mysqldump
	ExtraOpt string `ini:"ExtraOpt"` // other mysqldump options string to be appended
}

// LogicalLoadMysqldump the config of logical loading with mysql
type LogicalLoadMysqldump struct {
	BinPath  string `ini:"BinPath"`  // the binary path of mysql
	ExtraOpt string `ini:"ExtraOpt"` // other mysql options string to be appended(we use mysql to load backup)
}

func (f *LogicalBackup) ValidateFilter() error {
	if f.Databases != "" || f.Tables != "" || f.ExcludeDatabases != "" || f.ExcludeTables != "" {
		if f.Regex != "" || f.TablesList != "" {
			//return errors.Errorf("databases filter cannot be used with other filter")
			f.filterType = FilterTypeForm
			logger.Log.Warnf("filer type 'form' will ignore regex=%s or tables-list=%s", f.Regex, f.TablesList)
		} else {
			f.filterType = FilterTypeForm
		}
	} else {
		if f.Regex != "" && f.TablesList == "" {
			f.filterType = FilterTypeRegex
		} else if f.Regex == "" && f.TablesList != "" {
			f.filterType = FilterTypeTablesList
		} else if f.Regex == "" && f.TablesList == "" {
			return errors.New("no backup tables filters given")
		} else {
			return errors.Errorf("regex and tables-list filter cannot be used together")
		}
	}
	return nil
}

// IsFormFilterType form 优先级最高
// 在指定任意 databases tables exclude-databases exclude-tables 时生效
func (f *LogicalBackup) IsFormFilterType() bool {
	if f.Databases != "" || f.Tables != "" || f.ExcludeDatabases != "" || f.ExcludeTables != "" {
		return true
	}
	return false
}

func (f *LogicalBackup) GetFilterType() FilterType {
	return f.filterType
}

type FilterType string

const (
	// FilterTypeForm 表单格式: databases=db1,db2 tables=* exclude-databases exclude-tables
	FilterTypeForm       FilterType = "form"
	FilterTypeRegex      FilterType = "regex"
	FilterTypeTablesList FilterType = "tables"
)
