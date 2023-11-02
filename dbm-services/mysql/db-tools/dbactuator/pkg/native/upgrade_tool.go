/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package native

import (
	"context"
	"errors"
	"fmt"
	"math"
	"os"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/jmoiron/sqlx"
)

const (
	// MYSQL_5P0P48 TODO
	MYSQL_5P0P48 uint64 = 5000048
	// MYSQL_5P1P24 TODO
	MYSQL_5P1P24 uint64 = 5001024
	// MYSQL_5P1P29 TODO
	MYSQL_5P1P29 uint64 = 5001029
	// MYSQL_5P1P46 TODO
	MYSQL_5P1P46 uint64 = 5001046
	// MYSQL_5P5P1 TODO
	MYSQL_5P5P1 uint64 = 5005001
	// MYSQL_5P5P5 TODO
	MYSQL_5P5P5 uint64 = 5005005
	// MYSQL_5P5P11 TODO
	MYSQL_5P5P11 uint64 = 5005011
	// MYSQL_5P5P24 TODO
	MYSQL_5P5P24 uint64 = 5005024
	// MYSQL_5P6P24 TODO
	MYSQL_5P6P24 uint64 = 5006024
	// MYSQL_5P70 TODO
	MYSQL_5P70 uint64 = 5007000
	// MYSQL_5P60 TODO
	MYSQL_5P60 uint64 = 5006000
	// MYSQL_5P7P21 TODO
	MYSQL_5P7P21 uint64 = 5007021
	// MYSQL_8P0 TODO
	MYSQL_8P0 uint64 = 8000000
	// MYSQL_8P0P16 TODO
	MYSQL_8P0P16 uint64 = 8000016 // mysql_upgrade deprecated
	// MYSQL_8P0P18 TODO
	MYSQL_8P0P18 uint64 = 8000018
	// TMYSQL_1 TODO
	TMYSQL_1 uint64 = 1000000
	// TMYSQL_1P1 TODO
	TMYSQL_1P1 uint64 = 1001000
	// TMYSQL_1P2 TODO
	TMYSQL_1P2 uint64 = 1002000
	// TMYSQL_1P4 TODO
	TMYSQL_1P4 uint64 = 1004000
	// TMYSQL_2 TODO
	TMYSQL_2 uint64 = 2000000
	// TMYSQL_2P1 TODO
	TMYSQL_2P1 uint64 = 2001000
	// TMYSQL_2P1P1 TODO
	TMYSQL_2P1P1 uint64 = 2001001
	// TMYSQL_3 TODO
	TMYSQL_3 uint64 = 3000000
	// TMySQL_3P15 TODO
	TMySQL_3P15 uint64 = 3001005
)

// CheckColObject TODO
type CheckColObject struct {
	TableSchema string `db:"TABLE_SCHEMA"`
	TableName   string `db:"TABLE_NAME"`
	ColumnName  string `db:"COLUMN_NAME"`
}

// HasInvalidCode  check if contain the invalid chars
func (h *DbWorker) HasInvalidCode() (invalidObjs []CheckColObject, err error) {
	conn, err := h.GetSqlxDb().Connx(context.Background())
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	// set names
	_, err = conn.ExecContext(context.Background(), "set names utf8;")
	if err != nil {
		return nil, err
	}
	// set var
	_, err = conn.ExecContext(context.Background(), "set @var:=concat('%', convert(0xC39F using utf8), '%');")
	if err != nil {
		return nil, err
	}
	checksql := `select distinct a.TABLE_SCHEMA, a.TABLE_NAME, a.COLUMN_NAME from information_schema.STATISTICS a, 
				information_schema.COLUMNS b 
				where a.TABLE_SCHEMA = b.TABLE_SCHEMA 
				and a.TABLE_NAME = b.TABLE_NAME 
				and a.COLUMN_NAME = b.COLUMN_NAME 
				and (
					b.COLLATION_NAME = 'utf8_general_ci'
					or
					b.COLLATION_NAME = 'utf8_general_mysql500_ci' 
					or 
					b.COLLATION_NAME = 'ucs2_general_ci' 
					or 
					b.COLLATION_NAME = 'ucs2_general_mysql500_ci'
					) 
				and a.TABLE_SCHEMA <> 'mysql';`
	var checkObjects []CheckColObject
	if err = conn.SelectContext(context.Background(), &checkObjects, checksql); err != nil {
		return nil, err
	}
	for _, v := range checkObjects {
		var count int
		err = conn.GetContext(context.Background(), &count, "select count("+v.ColumnName+") from "+v.TableSchema+"."+
			v.TableName+
			" where "+v.ColumnName+" like @var collate utf8_bin ;")
		if err != nil {
			return nil, err
		}
		if count > 0 {
			invalidObjs = append(invalidObjs, v)
		}
	}
	return invalidObjs, nil
}

// CheckInstantAddColumnObj TODO
type CheckInstantAddColumnObj struct {
	Name      string `db:"NAME"`
	TableID   int    `db:"TABLE_ID"`
	NCols     int    `db:"N_COLS"`
	NCoreCols int    `db:"N_CORE_COLS"`
}

var (
	// ErrorUsedInstantAddColumnButValid TODO
	ErrorUsedInstantAddColumnButValid = errors.New("found usage of instant add column, but it is valid")
	// ErrorInvalidUsageOfInstantAddColumn TODO
	ErrorInvalidUsageOfInstantAddColumn = errors.New("found invalid usage of instant add column")
)

// CheckInstantAddColumn TODO
func (h *DbWorker) CheckInstantAddColumn() (err error) {
	var data []CheckInstantAddColumnObj
	err = h.Queryx(&data,
		"select NAME, TABLE_ID, N_COLS,N_CORE_COLS from INFORMATION_SCHEMA.INNODB_SYS_TABLES where N_COLS <> N_CORE_COLS")
	if err != nil {
		return err
	}
	usedInstantAddColumn := 0
	containInvalidAddColumn := 0
	for _, v := range data {
		usedInstantAddColumn = 1
		var flags []int
		err = h.Queryx(&flags,
			`select case (PRTYPE & 256) when 256 THEN 1 ELSE 0 END as DATA_NOT_NULL
			 from  INFORMATION_SCHEMA.INNODB_SYS_COLUMNS where TABLE_ID=?`, v.TableID)
		if err != nil {
			return err
		}
		i := 0
		beforeNull := 0
		afterNull := 0
		for _, vv := range flags {
			i++
			if vv == 0 {
				afterNull++
				if i <= v.NCoreCols {
					beforeNull++
				}
			}
		}
		a := int(math.Ceil(float64(beforeNull) / 8))
		b := int(math.Ceil(float64(afterNull) / 8))
		if a != b {
			containInvalidAddColumn = 1
			logger.Info("%s, column_num:%d, column_num_before_add:%d, null_num_before_add:%d, num_num_after_add:%d\n", v.Name,
				v.NCols, v.NCoreCols, beforeNull, afterNull)
		}
	}
	if containInvalidAddColumn > 0 {
		return ErrorInvalidUsageOfInstantAddColumn
	}
	if usedInstantAddColumn > 0 {
		return ErrorUsedInstantAddColumnButValid
	}
	return nil
}

// GetDeleteWithoutDropUser TODO
func (h *DbWorker) GetDeleteWithoutDropUser() (accounts []string, err error) {
	q := `
	select concat(user, '\@', host) as account
from mysql.db
where Delete_priv = 'Y'
    and Drop_priv = 'N'
union
select concat(user, '\@', host) as account
from mysql.tables_priv
where Table_priv like '%Delete%'
    and Table_priv not like '%Drop%'
	`
	err = h.Queryx(&accounts, q)
	return
}

// TableInfo  information_schema.table info
type TableInfo struct {
	TableSchema string `db:"TABLE_SCHEMA"`
	TableName   string `db:"TABLE_NAME"`
	TableType   string `db:"TABLE_TYPE"`
	Engine      string `db:"ENGINE"`
	RowFormat   string `db:"ROW_FORMAT"`
}

// CheckTableUpgrade TODO
func (h *DbWorker) CheckTableUpgrade(currentVersion, newVersion uint64) (err error) {
	type checkFunc struct {
		fn   func(currentVersion, newVersion uint64) error
		desc string
	}
	// 库表名关键字检查
	fns := []checkFunc{}
	fns = append(fns, checkFunc{
		fn:   h.tableNameKeyWordCheck,
		desc: "检查表名是否包含关键字",
	})
	fns = append(fns, checkFunc{
		fn:   h.colNameNameKeyWordCheck,
		desc: "检查字段是否包含关键字",
	})
	fns = append(fns, checkFunc{
		fn:   h.routineNameKeyWordCheck,
		desc: "存储过程名关键字检查",
	})
	fns = append(fns, checkFunc{
		fn:   h.eventNameKeyWordCheck,
		desc: "eventName关键字检查",
	})
	fns = append(fns, checkFunc{
		fn:   h.triggerNameKeyWordCheck,
		desc: "triggerName关键字检查"})
	fns = append(fns, checkFunc{
		fn:   h.viewNameKeyWordCheck,
		desc: "视图名关键字检查",
	})
	for _, f := range fns {
		logger.Info("start check %s ...", f.desc)
		if err = f.fn(currentVersion, newVersion); err != nil {
			logger.Error("when check %s,failed %s", f.desc, err.Error())
			return err
		}
	}
	type checkFuncNoparam struct {
		fn   func() error
		desc string
	}
	// 非法字符检查
	fnns := []checkFuncNoparam{}
	fnns = append(fnns, checkFuncNoparam{
		fn:   h.tableNameAsciiCodeCheck,
		desc: "检查库、表名中包含非法字符",
	})
	fnns = append(fnns, checkFuncNoparam{
		fn:   h.columnNameAsciiCodeCheck,
		desc: "检查列名中包含非法字符",
	})
	fnns = append(fnns, checkFuncNoparam{
		fn:   h.routineNameAsciiCodeCheck,
		desc: "存储过程名中包含非法字符",
	})
	fnns = append(fnns, checkFuncNoparam{
		fn:   h.triggerNameAsciiCodeCheck,
		desc: "触发器名中包含非法字符",
	})
	fnns = append(fnns, checkFuncNoparam{
		fn:   h.viewNameAsciiCodeCheck,
		desc: "视图名中包含非法字符",
	})
	fnns = append(fnns, checkFuncNoparam{
		fn:   h.udfCheck,
		desc: "检查是否包含自定义函数",
	})
	for _, f := range fnns {
		logger.Info("start check %s ...", f.desc)
		if err = f.fn(); err != nil {
			logger.Error("when check %s,failed %s", f.desc, err.Error())
			return err
		}
	}
	switch {
	// 当准备升级到8.0版本
	case newVersion >= MYSQL_8P0 && currentVersion < MYSQL_8P0:
		logger.Info("准备升级到8.0需要做这些额外的检查...")
		fns80 := []checkFuncNoparam{}
		fns80 = append(fns80, checkFuncNoparam{
			fn:   h.checkNonNativeSupportParttion,
			desc: "升级到MySQL8.0,必须将分区引起改成innodb或者ndb,不能有使用不支持本地分区的引擎创建分区表",
		})
		fns80 = append(fns80, checkFuncNoparam{
			fn:   h.checkParttionsInInnoSharedTableSpace,
			desc: "没有分区表在共享表空间,Before upgrading to 8.0 they need to be moved to file-per-table tablespace",
		})
		fns80 = append(fns80, checkFuncNoparam{
			fn:   h.foreignKeyNameLengthCheck,
			desc: "MySQL 8.0 限制外键名称不能超过 64 个字符,检查当前版本外键长度",
		})
		fns80 = append(fns80, checkFuncNoparam{
			fn:   h.enumSetTotalLengthTooLong,
			desc: "表或者存储过程的 ENUM/SET 的所有元素总长度超过 255 字符，会导致升级失败",
		})
		fns80 = append(fns80, checkFuncNoparam{
			fn:   h.viewNameLengthTooLong,
			desc: "视图列名不能超过 64 字符",
		})
		fns80 = append(fns80, checkFuncNoparam{
			fn:   h.datadicTablenameConflictsCheck,
			desc: "检查MySQL 系统数据库中与 MySQL 8.0 数据字典中同名的表",
		})
		for _, f := range fns80 {
			logger.Info("start check %s ...", f.desc)
			if err = f.fn(); err != nil {
				logger.Error("when check %s,failed %s", f.desc, err.Error())
				return err
			}
		}
	// 当准备升级到5.7版本
	case newVersion >= MYSQL_5P70 && currentVersion < MYSQL_5P70:
		// per-4.1 password check
		logger.Info("准备升级到MySQL5.7 需要做这些额外的检查...")
		fns57 := []checkFuncNoparam{}
		fns57 = append(fns57, checkFuncNoparam{
			fn:   h.passwordCheck,
			desc: "密码检查",
		})
		fns57 = append(fns57, checkFuncNoparam{
			fn:   h.partitionCheck,
			desc: "5.7分表有比较大的改动,暂时不支持本地升级",
		})
		fns57 = append(fns57, checkFuncNoparam{
			fn:   h.columnTypeCheck,
			desc: "MySQL5.7不支持year(2)字段类型,需要提前升级",
		})
		fns57 = append(fns57, checkFuncNoparam{
			fn:   h.tokudbEngineCheck,
			desc: "tokudb引擎检查",
		})
		for _, f := range fns57 {
			logger.Info("start check %s ...", f.desc)
			if err = f.fn(); err != nil {
				logger.Error("when check %s,failed %s", f.desc, err.Error())
				return err
			}
		}
	// 当准备升级到5.6版本
	case newVersion >= MYSQL_5P60 && currentVersion < MYSQL_5P60:
		// per-4.1 password check
		logger.Info("准备升级到MySQL5.6 需要做这些额外的检查...")
		if err = h.passwordCheck(); err != nil {
			return err
		}

	}
	return nil
}

func (h *DbWorker) getKeyWords(currentVersion, newVersion uint64) []string {
	ReservedWords := []string{"ACCESSIBLE", "LINEAR", "MASTER_SSL_VERIFY_SERVER_CERT", "RANGE", "READ_ONLY",
		"IGNORE_SERVER_IDS", "MASTER_HEARTBEAT_PERIOD", "MAXVALUE", "RESIGNAL", "SIGNAL", "SLOW"}
	// new added reserver words for MySQL5.6
	ReservedWords56 := []string{"GET", "IO_AFTER_GTIDS", "IO_BEFORE_GTIDS", "MASTER_BIND", "PARTITION"}
	// new added reserver words for MySQL5.7
	ReservedWords57 := []string{"GENERATED", "OPTIMIZER_COSTS", "STORED", "VIRTUAL", "PARTITION"}
	// new added reserver words for MySQL8.0
	ReservedWords80 := []string{"CUME_DIST", "DENSE_RANK", "EMPTY", "EXCEPT", "FIRST_VALUE", "GROUPING", "GROUPS",
		"JSON_TABLE", "LAG", "LAST_VALUE", "LATERAL", "LEAD", "NTH_VALUE", "NTILE", "OF", "OVER", "PERCENT_RANK", "RANK",
		"RECURSIVE", "ROW_NUMBER", "SYSTEM", "WINDOW"}
	switch {
	case newVersion >= MYSQL_8P0 && currentVersion < MYSQL_8P0:
		return append(ReservedWords, ReservedWords80...)
	case newVersion >= MYSQL_5P70 && currentVersion < MYSQL_5P70:
		return append(ReservedWords, ReservedWords57...)
	case newVersion >= MYSQL_5P60 && currentVersion < MYSQL_5P60:
		return append(ReservedWords, ReservedWords56...)
	default:
		return ReservedWords
	}
}

// tableNameKeyWordCheck TODO
func (h *DbWorker) tableNameKeyWordCheck(currentVersion, newVersion uint64) (err error) {
	var data []TableInfo
	q, args, err := sqlx.In(
		"select TABLE_SCHEMA,TABLE_NAME,TABLE_TYPE from information_schema.tables where table_name in (?)",
		h.getKeyWords(currentVersion, newVersion))
	if err != nil {
		return err
	}
	if err = h.Queryx(&data, q, args...); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid table name: %v", data)
	}
	return nil
}

// ColumnInfo TODO
type ColumnInfo struct {
	TableSchema string `db:"TABLE_SCHEMA"`
	TableName   string `db:"TABLE_NAME"`
	ColumnName  string `db:"COLUMN_NAME"`
}

func (h *DbWorker) colNameNameKeyWordCheck(currentVersion, newVersion uint64) (err error) {
	var data []ColumnInfo
	q, args, err := sqlx.In(
		"select TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME from information_schema.columns where column_name in (?)",
		h.getKeyWords(currentVersion, newVersion))
	if err != nil {
		return err
	}
	if err = h.Queryx(&data, q, args...); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

// RoutineInfo TODO
type RoutineInfo struct {
	RoutineSchema string `db:"ROUTINE_SCHEMA"`
	RoutineName   string `db:"ROUTINE_NAME"`
	RoutineType   string `db:"ROUTINE_TYPE"`
}

func (h *DbWorker) routineNameKeyWordCheck(currentVersion, newVersion uint64) (err error) {
	var data []RoutineInfo
	blacklist := []string{"ExtractValue", "FROM_BASE64", "GTID_SUBSET", "GTID_SUBTRACT", "INET6_ATON", "INET6_NTOA",
		"IS_IPV4_COMPAT", "IS_IPV4_MAPPED", "IS_IPV4", "IS_IPV6", "SQL_THREAD_WAIT_AFTER_GTIDS", "TO_BASE64", "TO_SECONDS",
		"UpdateXML", "UUID_SHORT", "VALIDATE_PASSWORD_STRENGTH", "WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS", "WEIGHT_STRING"}
	keywords := h.getKeyWords(currentVersion, newVersion)
	keywords = append(keywords, blacklist...)
	q, args, err := sqlx.In(
		"select ROUTINE_SCHEMA,ROUTINE_NAME,ROUTINE_TYPE from information_schema.routines where routine_name in (?)",
		keywords)
	if err != nil {
		return err
	}
	if err = h.Queryx(&data, q, args...); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

// TriggerInfo TODO
type TriggerInfo struct {
	TriggerSchema string `db:"TRIGGER_SCHEMA"`
	TriggerName   string `db:"TRIGGER_NAME"`
}

func (h *DbWorker) triggerNameKeyWordCheck(currentVersion, newVersion uint64) (err error) {
	var data []TriggerInfo
	q, args, err := sqlx.In(
		"select TRIGGER_SCHEMA,TRIGGER_NAME from information_schema.triggers where TRIGGER_NAME in (?)",
		h.getKeyWords(currentVersion, newVersion))
	if err != nil {
		return err
	}
	if err = h.Queryx(&data, q, args...); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

// EventInfo TODO
type EventInfo struct {
	EventSchema string `db:"EVENT_SCHEMA"`
	EventName   string `db:"EVENT_NAME"`
}

func (h *DbWorker) eventNameKeyWordCheck(currentVersion, newVersion uint64) (err error) {
	var data []EventInfo
	q, args, err := sqlx.In(
		"select EVENT_SCHEMA,EVENT_NAME from information_schema.events where EVENT_NAME in (?)",
		h.getKeyWords(currentVersion, newVersion))
	if err != nil {
		return err
	}
	if err = h.Queryx(&data, q, args...); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

// ViewInfo TODO
type ViewInfo struct {
	TableSchema string `db:"TABLE_SCHEMA"`
	TableName   string `db:"TABLE_NAME"`
	Definer     string `db:"DEFINER"`
}

func (h *DbWorker) viewNameKeyWordCheck(currentVersion, newVersion uint64) (err error) {
	var data []ViewInfo
	q, args, err := sqlx.In(
		"select TABLE_SCHEMA,TABLE_NAME,DEFINER from information_schema.VIEWS where TABLE_NAME  in (?)",
		h.getKeyWords(currentVersion, newVersion))
	if err != nil {
		return err
	}
	if err = h.Queryx(&data, q, args...); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

func (h *DbWorker) tableNameAsciiCodeCheck() (err error) {
	var data []TableInfo
	q := `
	select TABLE_SCHEMA,
    TABLE_NAME,
    TABLE_TYPE
from information_schema.tables
where TABLE_NAME <> convert(table_name using ASCII)
    or TABLE_SCHEMA <> convert(TABLE_SCHEMA using ASCII);
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

func (h *DbWorker) columnNameAsciiCodeCheck() (err error) {
	var data []ColumnInfo
	q := `
	select TABLE_SCHEMA,
    TABLE_NAME,
    COLUMN_NAME
from information_schema.columns
where column_name <> convert(column_name using ASCII)
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

func (h *DbWorker) columnTypeCheck() (err error) {
	var data []ColumnInfo
	err = h.Queryx(&data, `
		select TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME 
		from information_schema.COLUMNS where COLUMN_TYPE='year(2)' group by 1,2,3;
		`)
	if err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("mysql5.7 no longer supports year(2) column type  please change it to year(4) in upgrade,list: %v",
			data)
	}
	return nil
}

func (h *DbWorker) routineNameAsciiCodeCheck() (err error) {
	var data []RoutineInfo
	q := `
	select ROUTINE_SCHEMA,
    ROUTINE_NAME,
    ROUTINE_TYPE
from information_schema.routines
where routine_name <> convert(routine_name using ASCII);
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

func (h *DbWorker) triggerNameAsciiCodeCheck() (err error) {
	var data []TriggerInfo
	q := `
	select TRIGGER_SCHEMA,
    TRIGGER_NAME
from information_schema.triggers
where TRIGGER_NAME <> convert(TRIGGER_NAME using ASCII)
    or ACTION_STATEMENT <> convert(ACTION_STATEMENT using ASCII);
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

func (h *DbWorker) viewNameAsciiCodeCheck() (err error) {
	var data []ViewInfo
	q := `
	select TABLE_SCHEMA,
    TABLE_NAME,
    DEFINER
from information_schema.VIEWS
where TABLE_NAME <> convert(TABLE_NAME using ASCII);
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("found invalid column name: %v", data)
	}
	return nil
}

// ConvertInnodbRowFomart  匹配innodb行格式 并生成可以适配快速加字段的行格式
//
//	Tmysql 中小于5.7的版本需要支持快速加字段需要转变行格式成GCS
func (h *DbWorker) ConvertInnodbRowFomart(ver string, file *os.File) (err error) {
	dbs, err := h.ShowDatabases()
	if err != nil {
		return err
	}
	_, err = file.WriteString("set sql_log_bin=off;\n")
	if err != nil {
		return fmt.Errorf("wirte sql_log_bin=off failed %w", err)
	}
	for _, db := range cmutil.FilterOutStringSlice(dbs, cmutil.GetGcsSystemDatabases(ver)) {
		var tables []TableInfo
		err = h.Queryx(&tables,
			"select TABLE_SCHEMA, TABLE_NAME, ENGINE, ROW_FORMAT from information_schema.TABLES where TABLE_SCHEMA = ?", db)
		if err != nil {
			return fmt.Errorf("when get tables in %s,failed %w", db, err)
		}
		for _, tb := range tables {
			var werr error = nil
			if strings.ToLower(tb.Engine) == "innodb" {
				switch strings.ToLower(tb.RowFormat) {
				case "compact":
					_, werr = file.WriteString(fmt.Sprintf("/*!99000 alter table `%s`.`%s` row_format=GCS */;\n", tb.TableSchema,
						tb.TableName))
				case "dynamic":
					_, werr = file.WriteString(fmt.Sprintf("/*!99000 alter table `%s`.`%s` row_format=GCS_Dynamic */;\n",
						tb.TableSchema,
						tb.TableName))
				}
				if werr != nil {
					return werr
				}
			}
		}
	}
	return err
}

// RenameTokudbTable TODO
func (h *DbWorker) RenameTokudbTable(ver string, file *os.File) (err error) {
	dbs, err := h.ShowDatabases()
	if err != nil {
		return err
	}
	_, err = file.WriteString("set sql_log_bin=off;\n")
	if err != nil {
		return fmt.Errorf("wirte sql_log_bin=off failed %w", err)
	}
	for _, db := range cmutil.FilterOutStringSlice(dbs, cmutil.GetGcsSystemDatabases(ver)) {
		var tables []TableInfo
		err = h.Queryx(&tables,
			"select TABLE_SCHEMA, TABLE_NAME, ENGINE, ROW_FORMAT from information_schema.TABLES where TABLE_SCHEMA = ?", db)
		if err != nil {
			return fmt.Errorf("when get tables in %s,failed %w", db, err)
		}
		for _, tb := range tables {
			if strings.ToLower(tb.Engine) != "tokudb" {
				continue
			}
			renamesSqls := []string{}
			renamesSqls = append(renamesSqls, fmt.Sprintf("rename table `%s`.`%s` to `%s`.`%s`;\n", tb.TableSchema, tb.TableName,
				tb.TableSchema, tb.TableName+"_tokudb_backup_tmp"))
			renamesSqls = append(renamesSqls, fmt.Sprintf("rename table `%s`.`%s` to `%s`.`%s`;\n", tb.TableSchema,
				tb.TableName+"_tokudb_backup_tmp",
				tb.TableSchema, tb.TableName))
			for _, ql := range renamesSqls {
				_, werr := file.WriteString(ql)
				if werr != nil {
					return werr
				}
			}
		}
	}
	return err

}

// udfCheck 检查是否能存在自定义函数
func (h *DbWorker) udfCheck() (err error) {
	// sql_check_udf="select dl from mysql.func;"
	var count int
	err = h.Queryxs(&count, "select count(dl) from mysql.func")
	if err != nil {
		return err
	}
	if count > 0 {
		return fmt.Errorf("found udf,but it is not allowed")
	}
	return nil
}

// passwordCheck per-4.1 password check
func (h *DbWorker) passwordCheck() (err error) {
	var accounts []string
	err = h.Queryx(&accounts, "SELECT  concat(user,'@',host) as account FROM mysql.user WHERE LENGTH(password) = 16")
	if err != nil {
		return err
	}
	if len(accounts) > 0 {
		return fmt.Errorf("%v found password length 16,but it is not allowed", accounts)
	}
	return
}

// partitionCheck https://dev.mysql.com/doc/refman/5.7/en/upgrading-from-previous-series.html
// ----MySQL 5.7 specific checks
// Beginning with MySQL 5.7.6, the InnoDB storage engine uses its own built-in (“native”) partitioning
// handler for any new partitioned tables created using InnoDB.
// Partitioned InnoDB tables created in previous versions of MySQL are not automatically upgraded.
// You can easily upgrade such tables to use InnoDB native partitioning
// in MySQL 5.7.9 or later using either of the following methods:
// 如果mysql5.7 升级分区表
// 执行alter 分区表可能会花费很多时间，暂时不支持
// To upgrade an individual table from the generic partitioning handler to InnoDB native partitioning,
// execute the statement ALTER TABLE table_name UPGRADE PARTITIONING.
// To upgrade all InnoDB tables that use the generic partitioning
// handler to use the native partitioning handler instead, run mysql_upgrade.
func (h *DbWorker) partitionCheck() (err error) {
	var data []TableInfo
	q := `
	select TABLE_SCHEMA,
    TABLE_NAME,
    count(*)
from INFORMATION_SCHEMA.PARTITIONS
where PARTITION_NAME is not NULL
group by 1,
    2;
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("%v found partition name,but it is not allowed", data)
	}
	return nil
}

func (h *DbWorker) tokudbEngineCheck() (err error) {
	var data []TableInfo
	q := `
	select TABLE_SCHEMA,
    TABLE_NAME,
    ENGINE
from information_schema.TABLES
where ENGINE = 'TokuDB'
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("exists TokuDB table,but it is not allowed,%v", data)
	}
	return nil
}

// ----MySQL 8.0 specific checks
// https://dev.mysql.com/doc/refman/8.0/en/upgrading-from-previous-series.html#upgrade-configuration-changes

// datadicTablenameConflictsCheck TODO
// 3.1.2 MySQL 系统数据库中不能有与 MySQL 8.0 数据字典中同名的表
func (h *DbWorker) datadicTablenameConflictsCheck() (err error) {
	var data []TableInfo
	q := `
	SELECT TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE LOWER(TABLE_SCHEMA) = 'mysql'
    and LOWER(TABLE_NAME) IN (
        'catalogs',
        'character_sets',
        'check_constraints',
        'collations',
        'column_statistics',
        'column_type_elements',
        'columns',
        'dd_properties',
        'events',
        'foreign_key_column_usage',
        'foreign_keys',
        'index_column_usage',
        'index_partitions',
        'index_stats',
        'indexes',
        'parameter_type_elements',
        'parameters',
        'resource_groups',
        'routines',
        'schemata',
        'st_spatial_reference_systems',
        'table_partition_values',
        'table_partitions',
        'table_stats',
        'tables',
        'tablespace_files',
        'tablespaces',
        'triggers',
        'view_routine_usage',
        'view_table_usage'
    );
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("系统数据库中存在与 MySQL 8.0 数据字典中同名的表,具体有%v", data)
	}
	return nil
}

func (h *DbWorker) foreignKeyNameLengthCheck() (err error) {
	var data []TableInfo
	q := `
	SELECT TABLE_SCHEMA, TABLE_NAME
	FROM INFORMATION_SCHEMA.TABLES
	WHERE TABLE_NAME IN
	  (SELECT LEFT(SUBSTR(ID,INSTR(ID,'/')+1),
				   INSTR(SUBSTR(ID,INSTR(ID,'/')+1),'_ibfk_')-1)
	   FROM INFORMATION_SCHEMA.INNODB_SYS_FOREIGN
	   WHERE LENGTH(SUBSTR(ID,INSTR(ID,'/')+1))>64);
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("%v found foreign key name length > 64,but it is not allowed", data)
	}
	return nil
}

// checkNonNativeSupportParttion TODO
// A MySQL storage engine is now responsible for providing its own partitioning handler,
// and the MySQL server no longer provides generic partitioning support.
// InnoDB and NDB are the only storage engines that provide a native partitioning handler that is supported in MySQL 8.0
// A partitioned table using any other storage engine must be altered—either to convert it to InnoDB or NDB,
// or to remove its partitioning—before upgrading the server, else it cannot be used afterwards.
func (h *DbWorker) checkNonNativeSupportParttion() (err error) {
	var data []TableInfo
	q := `
	SELECT TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE ENGINE NOT IN ('innodb', 'ndbcluster')
    AND CREATE_OPTIONS LIKE '%partitioned%';
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("exists non-native support partition,but it is not allowed,%v", data)
	}
	return nil
}

// TableSpaceInfo TableSpaceInfo
type TableSpaceInfo struct {
	Name      string `db:"NAME"`
	Space     string `db:"SPACE"`
	SpaceType string `db:"SPACE_TYPE"`
}

// checkParttionsInInnoSharedTableSpace TODO
// 3.1.6 没有分区表在共享表空间
func (h *DbWorker) checkParttionsInInnoSharedTableSpace() (err error) {
	var data []TableSpaceInfo
	q := `
	SELECT DISTINCT NAME,
    SPACE,
    SPACE_TYPE
FROM INFORMATION_SCHEMA.INNODB_SYS_TABLES
WHERE NAME LIKE '%#P#%'
    AND SPACE_TYPE NOT LIKE 'Single';
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("exists partition in innodb shared tablespace,but it is not allowed,%v", data)
	}
	return nil
}

// enumSetTotalLengthTooLong TODO
// 3.1.5 表或者存储过程的 ENUM/SET 的所有元素总长度超过 255 字符，会导致升级失败
// EnumSetTotalLenghTooLong TODO
func (h *DbWorker) enumSetTotalLengthTooLong() (err error) {
	var data []ColumnInfo
	q := `
	select concat(TABLE_SCHEMA, ".", TABLE_NAME, ".", COLUMN_NAME) as schema_table_column
	from information_schema.columns
	where length(COLUMN_TYPE) > 255 + 8
		and TABLE_SCHEMA NOT IN (
			'INFORMATION_SCHEMA',
			'SYS',
			'PERFORMANCE_SCHEMA',
			'MYSQL'
		);
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("exists column type length > 255,but it is not allowed,%v", data)
	}
	return nil
}

// viewNameLengthTooLong 3.1.11 视图列名不能超过 64 字符
func (h *DbWorker) viewNameLengthTooLong() (err error) {
	var data []ColumnInfo
	q := `
	SELECT c.TABLE_SCHEMA,
    c.TABLE_NAME,
    c.COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS c
    JOIN INFORMATION_SCHEMA.TABLES t ON c.TABLE_NAME = t.TABLE_NAME
    and c.TABLE_SCHEMA = t.TABLE_SCHEMA
where c.TABLE_SCHEMA NOT IN (
        'INFORMATION_SCHEMA',
        'SYS',
        'PERFORMANCE_SCHEMA',
        'MYSQL'
    )
    AND t.TABLE_COMMENT = 'VIEW'
    AND length(c.COLUMN_NAME) >= 64;
	`
	if err = h.Queryx(&data, q); err != nil {
		return err
	}
	if len(data) > 0 {
		return fmt.Errorf("exists view column name length > 64,but it is not allowed,%v", data)
	}
	return nil
}

func (h *DbWorker) tableCommentIllegalChar() (err error) {
	conn, err := h.GetSqlxDb().Connx(context.Background())
	if err != nil {
		return err
	}
	defer conn.Close()
	rows, err := conn.QueryContext(context.Background(), "SELECT DISTINCT 1 FROM INFORMATION_SCHEMA.COLUMNS;")
	if err != nil {
		return err
	}
	defer rows.Close()
	var warnings []Warning
	if err = conn.SelectContext(context.Background(), &warnings, "show warnings;"); err != nil {
		return err
	}
	if len(warnings) <= 0 {
		return nil
	}
	logger.Error("get warnings %v", warnings)
	var errs []error
	for _, warning := range warnings {
		if warning.Code == 1366 {
			errs = append(errs, fmt.Errorf("非法comment %s", warning.Message))
		}
	}
	return errors.Join(errs...)
}
