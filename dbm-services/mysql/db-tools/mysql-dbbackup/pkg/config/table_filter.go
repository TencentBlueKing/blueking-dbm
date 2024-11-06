package config

import (
	"fmt"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// TableFilter 三种类型的过滤方式，互斥
// 1. databases, tables, exclude-databases, exclude-tables, 精确名字，通用，可用于 mydumper, mysqldump 导出的数据
// 2. tables-list, 精确 db 或者 db.table
// 3. regex 正则过滤，优先用于 myloader
// Regex myloader regex format
type TableFilter struct {
	Databases        string `ini:"Databases"`
	Tables           string `ini:"Tables"`
	ExcludeDatabases string `ini:"ExcludeDatabases"`
	ExcludeTables    string `ini:"ExcludeTables"`

	// TablesList db1.table1 format
	TablesList string `ini:"TablesList"`

	Regex string `ini:"Regex"`

	// 是否备份实例所有业务db
	isAllDatabases bool
	toolName       string
}

type FilterType string

const (
	// FilterTypeForm 表单格式: databases=db1,db2 tables=* exclude-databases exclude-tables
	FilterTypeForm       FilterType = "form"
	FilterTypeRegex      FilterType = "regex"
	FilterTypeTablesList FilterType = "tables"
	FilterTypeEmpty      FilterType = "empty"
	FilterTypeUnknown    FilterType = "unknown"
)

// GetFilterType 过滤器类型，form 优先级最高
// 在指定任意 databases tables exclude-databases exclude-tables 时生效
func (f *TableFilter) GetFilterType() FilterType {
	if f.Databases != "" || f.Tables != "" || f.ExcludeDatabases != "" || f.ExcludeTables != "" {
		//logger.Log.Warnf("filer type 'form' will ignore regex=%s or tables-list=%s", f.Regex, f.TablesList)
		return FilterTypeForm
	} else {
		if f.Regex == "" && f.TablesList != "" {
			return FilterTypeTablesList
		} else if f.Regex != "" && f.TablesList == "" {
			return FilterTypeRegex
		} else if f.Regex == "" && f.TablesList == "" {
			//return errors.New("no backup tables filters given")
			return FilterTypeEmpty
		}
	}
	return FilterTypeUnknown
}

func (f *TableFilter) ValidateFilter() error {
	if f.Databases != "" || f.Tables != "" || f.ExcludeDatabases != "" || f.ExcludeTables != "" { // FilterTypeForm
		if f.Regex == "" {
			filter, err := db_table_filter.NewFilter(
				strings.Split(f.Databases, ","),
				strings.Split(f.Tables, ","),
				strings.Split(f.ExcludeDatabases, ","),
				strings.Split(f.ExcludeTables, ","),
			)
			if err != nil {
				return err
			}
			f.Regex = filter.TableFilterRegex()
		}
		//logger.Log.Warnf("filter type 'form' will ignore regex=%s or tables-list=%s", f.Regex, f.TablesList)
	} else {
		if f.Regex != "" && f.TablesList != "" {
			return errors.Errorf("regex and tables-list filter cannot be used together")
		}
	}
	return nil
}

func (f *TableFilter) BuildArgsTableFilterForMydumper() (args []string, err error) {
	filterType := f.GetFilterType()
	if filterType == FilterTypeForm {
		tables := f.Tables
		databases := f.Databases
		excludeDatabases := f.ExcludeDatabases
		excludeTables := f.ExcludeTables
		if tables == "" {
			tables = "*"
		}
		if databases == "" {
			databases = "*"
		}

		dbList := strings.Split(databases, ",")
		tbList := strings.Split(tables, ",")
		dbListExclude := strings.Split(excludeDatabases, ",")
		tbListExclude := strings.Split(excludeTables, ",")
		filter, err := db_table_filter.NewFilter(dbList, tbList, dbListExclude, tbListExclude)
		if err != nil {
			return nil, err
		}
		regexStr := filter.TableFilterRegex()
		args = append(args, []string{"-x", fmt.Sprintf(`'%s'`, regexStr)}...)
		logger.Log.Error("myloader regex: ", regexStr)
	} else if filterType == FilterTypeTablesList {
		return nil, errors.Errorf("loader unsupport filter type '%s' yet", filterType)
	} else if f.Regex != "" { //
		args = append(args, []string{"-x", fmt.Sprintf(`'%s'`, f.Regex)}...)
	} else {
		// return nil, errors.Errorf("loader unsupport filter type '%s'", f.filterType)
		// all data
	}
	return args, nil
}
