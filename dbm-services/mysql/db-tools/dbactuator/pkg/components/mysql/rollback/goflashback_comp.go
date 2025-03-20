package rollback

import (
	"bytes"
	"encoding/csv"
	"fmt"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/filecontext"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

// GoFlashbackComp TODO
type GoFlashbackComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       GoFlashback              `json:"extend"`
}

// GoFlashback 库表闪回
// 暂不从备份系统下载 binlog
// GoFlashback 的导出属性，只用于传参，目的在于构造 flashback 参数
type GoFlashback struct {
	TargetTime   string           `json:"target_time" validate:"required"`
	StopTime     string           `json:"stop_time"`
	TgtInstance  native.InsObject `json:"tgt_instance" validate:"required"`
	FlashbackOpt *FlashbackOpt    `json:"recover_opt" validate:"required"`

	// 当 binlog_dir 不为空，表示 binlog 已下载；当为空时，目前只从本地软连接
	BinlogDir string `json:"binlog_dir"`
	// binlog列表，如果不提供，则自动从本地查找符合时间范围的 binlog
	BinlogFiles []string `json:"binlog_files"`
	// WorkDir binlog 解析所在目录，存放运行日志
	WorkDir string `json:"work_dir" validate:"required"`
	WorkID  string `json:"work_id"`
	// ParseConcurrency 解析binlog并发度
	ParseConcurrency int `json:"parse_concurrency"`
	// DirectWriteBack 直接回写原 db
	DirectWriteBack bool `json:"direct_write_back"`

	// binlog 下载到哪个目录
	binlogSaveDir string
	dbWorker      *native.DbWorker
	flashback     *restore.GoApplyBinlog
	tableFilter   *db_table_filter.DbTableFilter
	tablesInfo    []*native.TableSchema

	ShareContext *filecontext.FileContext `json:"-"`
}

// Init TODO
func (f *GoFlashback) Init() error {
	f.flashback = &restore.GoApplyBinlog{
		TgtInstance:        f.TgtInstance,
		WorkDir:            f.WorkDir,
		WorkID:             f.WorkID,
		ParseConcurrency:   f.ParseConcurrency,
		QuickMode:          true,
		SourceBinlogFormat: "ROW", // 这里只代表 flashback 要求 ROW 模式，源实例 binlog_format 在 PreCheck 里会判断
		ParseOnly:          true,
		BinlogOpt: &restore.GoMySQLBinlogUtil{
			Flashback:        true, // --flashback 模式
			DisableLogBin:    false,
			Idempotent:       true,
			Autocommit:       true,
			Databases:        f.FlashbackOpt.Databases,
			Tables:           f.FlashbackOpt.Tables,
			ExcludeDatabases: f.FlashbackOpt.DatabasesIgnore,
			ExcludeTables:    f.FlashbackOpt.TablesIgnore,
			//RowsFilter:            f.FlashbackOpt.RowsFilter,
			RowsEventType:         f.FlashbackOpt.RowsEventType,
			ConvRowsUpdateToWrite: f.FlashbackOpt.ConvRowsUpdateToWrite,
		},
		MySQLClientOpt: &restore.MySQLClientOpt{
			BinaryMode:       true,
			MaxAllowedPacket: 1073741824,
		},
	}
	f.flashback.StartTime = f.TargetTime
	if f.StopTime == "" {
		timeNow := time.Now()
		f.StopTime = timeNow.Local().Format(time.RFC3339)
	}
	f.flashback.StopTime = f.StopTime

	toolset, err := tools.NewToolSetWithPick(tools.ToolGoMysqlbinlog, tools.ToolMysqlclient)
	if err != nil {
		return err
	}
	if err = f.flashback.ToolSet.Merge(toolset); err != nil {
		return err
	}
	// 拼接 goapply-binlog 参数
	if err := f.flashback.Init(); err != nil {
		return err
	}
	f.dbWorker = f.flashback.GetDBWorker()
	return nil
}

// downloadBinlogFiles 将文件软连接到 downloadDir
func (f *GoFlashback) downloadBinlogFiles() error {
	f.binlogSaveDir = filepath.Join(f.flashback.GetTaskDir(), "binlog")
	if err := osutil.CheckAndMkdir("", f.binlogSaveDir); err != nil {
		return err
	}
	for _, fn := range f.flashback.BinlogFiles {
		srcFile := filepath.Join(f.flashback.BinlogDir, fn)
		dstFile := filepath.Join(f.binlogSaveDir, fn)
		if err := osutil.MakeSoftLink(srcFile, dstFile, true); err != nil {
			return errors.Wrap(err, dstFile)
		}
	}
	// 在后续 binlog-recover 环节，使用下载目录
	f.flashback.BinlogDir = f.binlogSaveDir
	return nil
}

// getBinlogFilesLocal 从本地实例查找并过滤 binlog
// fromDir 指定从哪个目录找 binlog
func (f *GoFlashback) getBinlogFilesLocal() (int64, error) {
	if len(f.BinlogFiles) == 0 {
		// 临时关闭 binlog 删除
		binlogDir, namePrefix, err := f.dbWorker.GetBinlogDir(f.TgtInstance.Port)
		if err != nil {
			return 0, err
		} else {
			logger.Info("binlogDir=%s namePrefix=%s", binlogDir, namePrefix)
		}
		binlogFiles, err := f.flashback.GetBinlogFilesFromDir(binlogDir, namePrefix)
		if err != nil {
			return 0, err
		}
		if len(binlogFiles) == 0 {
			logger.Warn("no binlog files found from %s", binlogDir)
		}
		f.flashback.BinlogDir = binlogDir // 实例真实 binlog dir
		f.flashback.BinlogFiles = binlogFiles
	}
	// flush logs 滚动 binlog
	if _, err := f.dbWorker.ExecWithTimeout(5*time.Second, "FLUSH LOGS"); err != nil {
		return 0, err
	}
	return f.flashback.FilterBinlogFiles()
}

// PreCheck 检查版本、实例角色、 binlog 格式
// 目前只考虑 binlog 在本地的 flashback，不从远端下载
func (f *GoFlashback) PreCheck() error {
	var err error
	if err = f.checkVersionAndVars(); err != nil {
		return err
	}
	if err = f.checkDBRole(); err != nil {
		return err
	}
	if err = f.checkDBTableExists(); err != nil {
		return err
	}
	//if err = f.checkDBTableInUse(); err != nil {
	//	return err
	//}

	if f.FlashbackOpt.RowsFilter != "" {
		rowsFilterExpr := f.FlashbackOpt.RowsFilter
		var columnNames, columnPositions []string
		var columnInfo native.TableColumnInfo
		if guessRowsFilterType(rowsFilterExpr) < 0 {
			// 如果是 csv 格式
			buf := bytes.NewBufferString(rowsFilterExpr)
			csvReader := csv.NewReader(buf)
			records, err := csvReader.ReadAll()
			if err != nil {
				return errors.WithMessagef(err, "Unable to parse file as CSV for")
			}
			if len(records) <= 1 {
				return errors.Errorf("error csv format")
			}

			csvHeader := records[0]
			_, columnInfo, err = f.checkTableColumnExists(csvHeader)
			if err != nil {
				return err
			}
			logger.Info("table column info:%+v", columnInfo)
			lines := strings.Split(rowsFilterExpr, "\n")
			//lines[0] = strings.Join(columnPositions, ",")
			for i, originalColumnName := range csvHeader {
				colPosName := fmt.Sprintf("col[%d]", columnInfo[originalColumnName].ColPos-1)
				newColumnName := fmt.Sprintf("%s:%s", colPosName, columnInfo[originalColumnName].ColType)
				records[0][i] = newColumnName
			}
			lines[0] = strings.Join(records[0], ",")
			logger.Info("table column name with position:%+v", lines[0])
			f.FlashbackOpt.RowsFilter = strings.Join(lines, "\n")
		} else {
			// 如果是 go-expr 格式
			columnNames = findColumnNamesFromRowsFilter(rowsFilterExpr)
			columnPositions, columnInfo, err = f.checkTableColumnExists(columnNames)
			if err != nil {
				return err
			}
			f.FlashbackOpt.RowsFilter = replaceColumnNamesWithPosition(rowsFilterExpr, columnNames, columnPositions)
		}
		f.flashback.BinlogOpt.RowsFilter = f.FlashbackOpt.RowsFilter
	}

	if f.BinlogDir == "" { // 没有指定 binlog 目录，目前是自动从 实例 binlog 目录本地找，并做软链
		if totalSize, err := f.getBinlogFilesLocal(); err != nil {
			return err
		} else {
			// 暂定 2 倍 binlog 大小
			diskSizeNeedKB := (totalSize / 1024) * 2
			logger.Info("parse binlog need disk size %d KB", diskSizeNeedKB)
		}
		if err = f.downloadBinlogFiles(); err != nil {
			return err
		}
	}
	if err = f.flashback.PreCheck(); err != nil {
		return err
	}
	return nil
}

// findColumnNamesFromRowsFilter 从行过滤器里面，找出列名，格式 @columnName1 == 111 and @columnName2 == aaa
// 注意，这里不去重
func findColumnNamesFromRowsFilter(rowsFilterExpr string) []string {
	columnReg := regexp.MustCompile(`@\w+`)
	matches := columnReg.FindAllString(rowsFilterExpr, -1)
	var columnNames []string
	for _, m := range matches {
		columnNames = append(columnNames, strings.TrimLeft(m, "@"))
	}
	return columnNames
}

// replaceColumnNamesWithPosition 行过滤器列名替换
// 把 @columnName1 == 111 and @columnName2 == aaa 变成 col[0] == 111 and col[1] == aaa
func replaceColumnNamesWithPosition(rowsFilterExpr string, columnNames, columnPositions []string) string {
	for i, columnName := range columnNames {
		col := "@" + columnName
		rowsFilterExpr = strings.ReplaceAll(rowsFilterExpr, col, columnPositions[i])
	}
	return rowsFilterExpr
}

// guessRowsFilterType 1:expr, -1:csv
func guessRowsFilterType(rowsFilterExpr string) int {
	if !strings.Contains(rowsFilterExpr, "\n") {
		return 1
	}
	// https://expr-lang.org/docs/language-definition
	exprKeyword := []string{"==", "!=", "<", ">", "<=", ">=", "&&", "||", "!",
		" and ", " AND ", " or ", " OR ", " not ", " NOT ", " in ", " IN "}
	for _, keyword := range exprKeyword {
		if strings.Contains(rowsFilterExpr, keyword) {
			return 1
		}
	}
	return -1
}

// PhasePrepare parse binlog
// 检查版本、实例角色、 binlog 格式
func (f *GoFlashback) PhasePrepare() (err error) {
	if err = f.flashback.Start(); err != nil {
		return err
	}
	logger.Info("write context to %s", f.ShareContext.GetContextFilePath())
	if err = f.ShareContext.Set("taskDir", f.flashback.GetTaskDir(), false); err != nil {
		return err
	}
	if err = f.ShareContext.Set("scriptName", f.flashback.GetScriptName(), false); err != nil {
		return err
	}
	if err = f.ShareContext.Save(); err != nil {
		return err
	}
	return nil
}

// PhaseExecute import binlog
func (f *GoFlashback) PhaseExecute() error {
	logger.Info("read context from %s", f.ShareContext.GetContextFilePath())
	taskDir, err := f.ShareContext.GetString("taskDir")
	if err != nil {
		return err
	}
	scriptName, err := f.ShareContext.GetString("scriptName")
	if err != nil {
		return err
	}
	f.dbWorker, err = f.TgtInstance.Conn()
	if err != nil {
		return err
	}
	defer f.dbWorker.Close()

	if err := restore.BinlogImport(taskDir, scriptName, f.dbWorker); err != nil {
		return err
	}
	return nil
}

// Start 检查版本、实例角色、 binlog 格式
// run parse and import binlog
func (f *GoFlashback) Start() error {
	if err := f.flashback.Start(); err != nil {
		return err
	}
	if err := f.flashback.Import(); err != nil {
		return err
	}
	return nil
}

// Example TODO
func (c *GoFlashbackComp) Example() interface{} {
	return GoFlashbackComp{
		Params: GoFlashback{
			flashback:        &restore.GoApplyBinlog{},
			TgtInstance:      common.InstanceObjExample,
			TargetTime:       "2022-11-11 00:00:01",
			WorkDir:          "/data/dbbak",
			BinlogDir:        "",
			ParseConcurrency: 2,
			FlashbackOpt: &FlashbackOpt{
				Databases:  []string{"db1", "db2"},
				Tables:     []string{"tb1", "tb2"},
				RowsFilter: "col[0]==100",
			},
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
}
