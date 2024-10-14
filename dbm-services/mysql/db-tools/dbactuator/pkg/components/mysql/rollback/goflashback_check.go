package rollback

import (
	errs "errors"
	"fmt"
	"regexp"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"

	"github.com/hashicorp/go-version"
	"github.com/pkg/errors"
)

func (f *GoFlashback) checkVersionAndVars() error {
	// binlog_format
	rowReg := regexp.MustCompile(`(?i)row`)
	fullReg := regexp.MustCompile(`(?i)full`)
	if val, err := f.dbWorker.GetSingleGlobalVar("binlog_format"); err != nil {
		return err
	} else if rowReg.MatchString(val) == false {
		return errors.Errorf("binlog_format=%s should be ROW", val)
	}
	// binlog_row_image
	flashbackAtLeastVer, _ := version.NewVersion("5.5.24")
	flashbackVer90, _ := version.NewVersion("9.0.0")
	fullrowAtLeastVer, _ := version.NewVersion("5.6.24") // 该版本之后才有 binlog_row_image
	if val, err := f.dbWorker.SelectVersion(); err != nil {
		return err
	} else {
		curInstVersion, err := version.NewVersion(val)
		if err != nil {
			return errors.Wrapf(err, "invalid version %s", val)
		}
		if curInstVersion.LessThan(flashbackAtLeastVer) || curInstVersion.GreaterThan(flashbackVer90) {
			return errors.Errorf("mysql version %s does not support flashback", curInstVersion)
		} else if curInstVersion.GreaterThan(fullrowAtLeastVer) {
			if val, err := f.dbWorker.GetSingleGlobalVar("binlog_row_image"); err != nil {
				return err
			} else if fullReg.MatchString(val) == false {
				return errors.Errorf("binlog_row_image=%s should be FULL", val)
			}
		}
	}
	return nil
}

func (f *GoFlashback) checkDBTableExists() error {
	// 检查库是否存在
	tableFilter, err := db_table_filter.NewFilter(
		f.FlashbackOpt.Databases, f.FlashbackOpt.Tables, f.FlashbackOpt.DatabasesIgnore, f.FlashbackOpt.TablesIgnore)
	if err != nil {
		return err
	}
	f.tableFilter = tableFilter
	dbTables, err := tableFilter.GetTablesByConnRaw(f.dbWorker.Db)
	if err != nil {
		return err
	}
	if len(dbTables) == 0 {
		return errors.Errorf("cannot find any tables match the filter")
	} else {
		logger.Info("tables to flashback %+v", dbTables)
	}
	for dbName, tables := range dbTables {
		for _, tbName := range tables {
			tableSchema := native.TableSchema{
				DbName:          dbName,
				TableName:       tbName,
				DbTableFullname: fmt.Sprintf("%s.%s", dbName, tbName),
			}
			f.tablesInfo = append(f.tablesInfo, &tableSchema)
		}
	}
	return nil
}

func (f *GoFlashback) checkDBTableInUse() error {

	// 检查表是否在使用
	var err2 error
	if openTables, err := f.dbWorker.ShowOpenTables(6 * time.Second); err != nil {
		return err
	} else {
		openTablesList := []string{}
		for _, dbt := range openTables {
			openTablesList = append(openTablesList, fmt.Sprintf("%s.%s", dbt.Database, dbt.Table))
		}
		logger.Info("tables opened %v", openTablesList)
		for _, tableInfo := range f.tablesInfo {
			if util.StringsHas(openTablesList, tableInfo.DbTableFullname) {
				err2 = errs.Join(err2, errors.Errorf("table is still opened %s", tableInfo.DbTableFullname))
			}
		}
		if err2 != nil {
			return err2
		}
	}
	return nil
}

func (f *GoFlashback) checkTableColumnExists(columnNames []string) ([]string, error) {
	var err error
	var columnsInfo native.TableColumnInfo
	for i, tableInfo := range f.tablesInfo {
		columnsInfo, err = native.GetOneTableColumns(f.dbWorker, tableInfo.DbName, tableInfo.TableName)
		if err != nil {
			return nil, err
		}
		f.tablesInfo[i].ColumnMap = columnsInfo
	}
	var err2 error
	var columnPositions []string
	for _, colName := range columnNames {
		// 判断列名，在不同的表里的位置是否相同
		firstTableName := ""
		colPosFromFirstTable := -1
		for _, tableInfo := range f.tablesInfo {
			if colDef, ok := tableInfo.ColumnMap[colName]; ok {
				if colPosFromFirstTable < 0 {
					colPosFromFirstTable = colDef.ColPos
					firstTableName = tableInfo.DbTableFullname
					colPosConverted := fmt.Sprintf("col[%d]", colPosFromFirstTable-1) // gomysqlbinlog
					columnPositions = append(columnPositions, colPosConverted)
					continue
				} else if colPosFromFirstTable != colDef.ColPos {
					err2 = errs.Join(err2, fmt.Errorf("column %s position %d from table %s is not same with %s",
						colName, colDef.ColPos, tableInfo.DbTableFullname, firstTableName))
				}
			} else {
				err2 = errs.Join(err2, errors.Errorf("column not found %s from table %s", colName, tableInfo.DbTableFullname))
			}
		}
	}
	if err2 != nil {
		return nil, err2
	}
	if len(columnNames) != len(columnPositions) {
		return nil, errors.Errorf("columnNames %v count dosnot match columnPositions %v", columnNames, columnPositions)
	}
	return columnPositions, nil
	/*
		// dbName tbName 必须是完整的表名
		for _, col := range columnNames {
			realColName := strings.Split(col, ":")
			isHex := false
			isSigned := false
			if len(realColName) == 2 {
				if realColName[1] == "hex" {
					isHex = true
				} else if realColName[1] == "signed" {
					isSigned = true
				} else if realColName[1] == "unsigned" {
					isSigned = false
				} else {
					return nil, errors.Errorf("column name error format %s", col)
				}
			}
			if val, ok := columnInfo[realColName[0]]; ok {
				//newCol := "@" + val.ColPos
				position := cast.ToInt(val.ColPos)
				newCol := fmt.Sprintf("col[%d]", position-1)
				if isHex {
					newCol += ":hex"
				}
				if isSigned {
					newCol += ":signed"
				}
				colPosStr = append(colPosStr, newCol)
			} else {
				return nil, errors.Errorf("column not found %s", realColName[0])
			}
		}
		// return col[1]:hex,col[0]
		return colPosStr, nil
	*/
}

func (f *GoFlashback) checkInstanceSkipped() error {
	return nil
}

func (f *GoFlashback) checkDBRole() error {
	// 从备份/监控配置里面获取 db_role
	// 从 show slave status 里面判断角色
	if slaveStatus, err := f.dbWorker.ShowSlaveStatus(); err != nil {
		return err
	} else {
		if slaveStatus.MasterHost != "" {
			return errors.New("target_instance should not be a slave")
		}
	}
	return nil
}

func (f *GoFlashback) checkDiskSpace() error {
	return nil
}
