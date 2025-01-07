/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package syntax

import (
	"strings"

	"github.com/samber/lo"

	util "dbm-services/common/go-pubpkg/cmutil"
)

const (
	// AlterTypeAddColumn add_column
	AlterTypeAddColumn = "add_column"

	// SQLTypeCreateTable is creat table sql
	SQLTypeCreateTable = "create_table"
	// SQLTypeCreateDb ise create database sql
	SQLTypeCreateDb = "create_db"
	// SQLTypeCreateFunction is create function sql
	SQLTypeCreateFunction = "create_function"
	// SQLTypeCreateTrigger is create trigger sql
	SQLTypeCreateTrigger = "create_trigger"
	// SQLTypeCreateEvent  is create event sql
	SQLTypeCreateEvent = "create_event"
	// SQLTypeCreateProcedure is create procedure sql
	SQLTypeCreateProcedure = "create_procedure"
	// SQLTypeCreateView is create view sql
	SQLTypeCreateView = "create_view"

	// SQLTypeAlterTable is alter table sql
	SQLTypeAlterTable = "alter_table"
	// SQLTypeDelete is delete sql
	SQLTypeDelete = "delete"
	// SQLTypeUpdate is update sql
	SQLTypeUpdate = "update"
	// SQLTypeUseDb is use db sql
	SQLTypeUseDb = "change_db"
	// SQLTypeInsertSelect insert select sql
	SQLTypeInsertSelect = "insert_select"
	// SQLTypeRelaceSelect replace select sql
	SQLTypeRelaceSelect = "replace_select"
	// SQLTypeDropTable drop table sql
	SQLTypeDropTable = "drop_table"
	// SQLTypeCreateIndex is creat table sql
	SQLTypeCreateIndex = "create_index"
)

// NotAllowedDefaulValColMap 不允许默认值的字段
var NotAllowedDefaulValColMap map[string]struct{}

func init() {
	NotAllowedDefaulValColMap = lo.SliceToMap([]string{"json", "tinyblob", "blob", "mediumblob", "longblob"},
		func(s string) (string, struct{}) {
			return s, struct{}{}
		})
}

// ColDef mysql column definition
type ColDef struct {
	Type                string      `json:"type"`
	ColName             string      `json:"col_name"`
	DataType            string      `json:"data_type"`
	FieldLength         int         `json:"field_length"`
	Nullable            bool        `json:"nullable"`
	DefaultVal          *DefaultVal `json:"default_val"`
	AutoIncrement       bool        `json:"auto_increment"`
	UniqueKey           bool        `json:"unique_key"`
	PrimaryKey          bool        `json:"primary_key"`
	Comment             string      `json:"comment"`
	CharacterSet        string      `json:"character_set"`
	Collate             string      `json:"collate"`
	ReferenceDefinition interface{} `json:"reference_definition"`
}

// IsNotAllowDefaulValCol tendbcluster 不允许某些类型的字段存在默认值的字段
func (c ColDef) IsNotAllowDefaulValCol() bool {
	if _, ok := NotAllowedDefaulValColMap[c.DataType]; ok {
		if c.DefaultVal != nil {
			return true
		}
	}
	return false
}

// DefaultVal column default value
type DefaultVal struct {
	Type  string `json:"type"`
	Value string `json:"value"`
}

// KeyDef mysql index definition
type KeyDef struct {
	Type     string `json:"type"`
	KeyName  string `json:"key_name"`
	KeyParts []struct {
		ColName string `json:"col_name"`
		KeyLen  int    `json:"key_len"`
	} `json:"key_parts"`
	KeyAlg              string      `json:"key_alg"`
	UniqueKey           bool        `json:"unique_key"`
	PrimaryKey          bool        `json:"primary_key"`
	Comment             string      `json:"comment"`
	ForeignKey          bool        `json:"foreign_key"`
	ReferenceDefinition interface{} `json:"reference_definition"`
}

// TableOption mysql table option definition
type TableOption struct {
	Key   string      `json:"key"`
	Value interface{} `json:"value"`
}

// ConverTableOptionToMap convert table option to map
func ConverTableOptionToMap(options []TableOption) map[string]interface{} {
	r := make(map[string]interface{})
	for _, v := range options {
		if !util.IsEmpty(v.Key) {
			r[v.Key] = v.Value
		}
	}
	return r
}

// CommDDLResult mysql common ddl tmysqlparse result
type CommDDLResult struct {
	QueryID   int    `json:"query_id"`
	Command   string `json:"command"`
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
}

// CreateTableResult  tmysqlparse create table result
type CreateTableResult struct {
	QueryID             int    `json:"query_id"`
	Command             string `json:"command"`
	DbName              string `json:"db_name"`
	TableName           string `json:"table_name"`
	IsTemporary         bool   `json:"is_temporary"`
	IfNotExists         bool   `json:"if_not_exists"`
	IsCreateTableLike   bool   `json:"is_create_table_like"`
	IsCreateTableSelect bool   `json:"is_create_table_select"`
	CreateDefinitions   struct {
		ColDefs []ColDef `json:"col_defs"`
		KeyDefs []KeyDef `json:"key_defs"`
	} `json:"create_definitions"`
	TableOptions     []TableOption          `json:"table_options,omitempty"`
	TableOptionMap   map[string]interface{} `json:"-"`
	PartitionOptions interface{}            `json:"partition_options"`
}

// CreateDBResult tmysqlparse create db result
type CreateDBResult struct {
	QueryID      int    `json:"query_id"`
	Command      string `json:"command"`
	DbName       string `json:"db_name"`
	CharacterSet string `json:"character_set"`
	Collate      string `json:"collate"`
}

// AlterTableResult tmysqlparse alter table result
type AlterTableResult struct {
	QueryID          int            `json:"query_id"`
	Command          string         `json:"command"`
	DbName           string         `json:"db_name"`
	TableName        string         `json:"table_name"`
	AlterCommands    []AlterCommand `json:"alter_commands"`
	PartitionOptions interface{}    `json:"partition_options"`
}

// AlterCommand tmysqlparse alter table result
type AlterCommand struct {
	Type         string        `json:"type"`
	ColDef       ColDef        `json:"col_def,omitempty"`
	After        string        `json:"after,omitempty"`
	KeyDef       KeyDef        `json:"key_def,omitempty"`
	DropPrimary  bool          `json:"drop_primary,omitempty"`
	DropForeign  bool          `json:"drop_foreign,omitempty"`
	DbName       string        `json:"db_name,omitempty"`
	TableName    string        `json:"table_name,omitempty"`
	OldKeyName   string        `json:"old_key_name,omitempty"`
	NewKeyName   string        `json:"new_key_name,omitempty"`
	TableOptions []TableOption `json:"table_options,omitempty"`
	Algorithm    string        `json:"algorithm,omitempty"`
	Lock         string        `json:"lock,omitempty"`
}

// ChangeDbResult mysqlparse change db result
type ChangeDbResult struct {
	QueryID int    `json:"query_id"`
	Command string `json:"command"`
	DbName  string `json:"db_name"`
}

// ErrorResult syntax error result
type ErrorResult struct {
	QueryID   int    `json:"query_id"`
	Command   string `json:"command"`
	ErrorCode int    `json:"error_code,omitempty"`
	ErrorMsg  string `json:"error_msg,omitempty"`
}

// ParseBase parse base
type ParseBase struct {
	QueryId     int    `json:"query_id"`
	Command     string `json:"command"`
	QueryString string `json:"query_string,omitempty"`
}

// ParseLineQueryBase parse line query base
type ParseLineQueryBase struct {
	QueryId         int    `json:"query_id"`
	Command         string `json:"command"`
	DbName          string `json:"db_name,omitempty"`
	QueryString     string `json:"query_string,omitempty"`
	ErrorCode       int    `json:"error_code,omitempty"`
	ErrorMsg        string `json:"error_msg,omitempty"`
	MinMySQLVersion int    `json:"min_mysql_version"`
	MaxMySQLVersion int    `json:"max_my_sql_version"`
}

// IsSysDb sql modify target db is sys db
func (p ParseLineQueryBase) IsSysDb() bool {
	return lo.Contains([]string{"mysql", "information_schema", "performance_schema", "sys"}, strings.ToLower(p.DbName))
}

// UserHost user host
type UserHost struct {
	User string `json:"user"`
	Host string `json:"host"`
}

// CreateView tmysqlparse create view result
type CreateView struct {
	ParseBase
	DbName      string   `json:"db_name,omitempty"`
	ViewName    string   `json:"view_name,omitempty"`
	FieldNames  []string `json:"field_names,omitempty"`
	Definer     UserHost `json:"definer,omitempty"`
	Algorithm   string   `json:"algorithm,omitempty"`
	SqlSecurity string   `json:"sql_security,omitempty"`
	AsSelect    string   `json:"as_select,omitempty"`
	CheckOption string   `json:"check_option,omitempty"`
}

// CreateProcedure tmysqlparse create proceduce result
type CreateProcedure struct {
	ParseBase
	Definer     UserHost `json:"definer,omitempty"`
	SpName      string   `json:"sp_name,omitempty"`
	SqlSecurity string   `json:"sql_security,omitempty"`
	DataAccess  string   `json:"data_access,omitempty"`
}

// CreateTrigger  tmysqlparse create trigger result
type CreateTrigger struct {
	ParseBase
	Definer      UserHost `json:"definer,omitempty"`
	TriggerName  string   `json:"trigger_name,omitempty"`
	TableName    string   `json:"table_name"`
	TriggerEvent string   `json:"trigger_event"`
}

// CreateFunction tmysqlparse create function result
type CreateFunction struct {
	ParseBase
	Definer UserHost `json:"definer,omitempty"`
	// TODO
}

// CreateEvent  tmysqlparse create event result
type CreateEvent struct {
	ParseBase
	Definer UserHost `json:"definer,omitempty"`
	// TODO
}

// CreateIndex  tmysqlparse create index result
type CreateIndex struct {
	ParseBase
	DbName    string   `json:"db_name,omitempty"`
	TableName string   `json:"table_name"`
	KeyDefs   []KeyDef `json:"key_defs"`
	Algorithm string   `json:"algorithm,omitempty"`
	Lock      string   `json:"lock,omitempty"`
}

// DeleteResult tmysqlparse delete result
type DeleteResult struct {
	ParseBase
	DbName    string `json:"db_name,omitempty"`
	TableName string `json:"table_name"`
	HasWhere  bool   `json:"has_where"`
	Limit     int    `json:"limit"`
}

// UpdateResult tmysqlparse update result
type UpdateResult struct {
	ParseBase
	DbName           string `json:"db_name,omitempty"`
	TableName        string `json:"table_name"`
	UpdateLockOption string `json:"update_lock_option"`
	HasIgnore        bool   `json:"has_ignore"`
	HasWhere         bool   `json:"has_where"`
	Limit            int    `json:"limit"`
}

// ParseIncludeTableBase parse include table
type ParseIncludeTableBase struct {
	QueryID   int    `json:"query_id"`
	Command   string `json:"command"`
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
}
