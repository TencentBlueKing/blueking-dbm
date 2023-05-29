package rollback

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"
	"io/ioutil"
	"regexp"
	"strings"
	"time"

	"github.com/hashicorp/go-version"
	"github.com/pkg/errors"
)

// Flashback 库表闪回
// 暂不从备份系统下载 binlog
type Flashback struct {
	FlashbackBinlog
	// 闪回的目标时间点，对应 recover-binlog 的 start_time, 精确到秒。目标实例的时区
	TargetTime string `json:"target_time" validate:"required"`
	StopTime   string `json:"stop_time"`
	dbWorker   *native.DbWorker
	recover    restore.RecoverBinlog
}

// FlashbackBinlog TODO
type FlashbackBinlog struct {
	TgtInstance native.InsObject `json:"tgt_instance" validate:"required"`
	RecoverOpt  *RecoverOpt      `json:"recover_opt" validate:"required"`
	// 当 binlog_dir 不为空，表示 binlog 已下载；当为空时，目前只从本地软连接
	BinlogDir string `json:"binlog_dir"`
	// binlog列表，如果不提供，则自动从本地查找符合时间范围的 binlog
	BinlogFiles []string `json:"binlog_files"`
	// binlog 解析所在目录，存放运行日志
	WorkDir string `json:"work_dir" validate:"required"`
	WorkID  string `json:"work_id"`
	// 解析binlog并发度
	ParseConcurrency int `json:"parse_concurrency"`
	// 恢复用到的客户端工具，不提供时会有默认值
	tools.ToolSet

	// binlog 下载到哪个目录
	binlogSaveDir string
}

// RecoverOpt TODO
type RecoverOpt struct {
	// row event 解析指定 databases
	Databases []string `json:"databases,omitempty"`
	// row event 解析指定 tables
	Tables []string `json:"tables,omitempty"`
	// row event 解析指定 忽略 databases
	DatabasesIgnore []string `json:"databases_ignore,omitempty"`
	// row event 解析指定 忽略 tables
	TablesIgnore []string `json:"tables_ignore,omitempty"`
	// 暂不支持行级闪回
	FilterRows string `json:"filter_rows"`
}

// getBinlogFiles 从本地实例查找并过滤 binlog
// fromDir 指定从哪个目录找 binlog
func (f *Flashback) getBinlogFiles(fromDir string) (int64, error) {
	if fromDir != "" {
		f.recover.BinlogDir = fromDir
	}
	if len(f.BinlogFiles) != 0 {
		f.recover.BinlogFiles = f.BinlogFiles
	} else {
		if binlogDir, binlogFiles, err := f.getBinlogFilesLocal(); err != nil {
			return 0, err
		} else {
			f.recover.BinlogDir = binlogDir // 实例真实 binlog dir
			f.recover.BinlogFiles = binlogFiles
		}
	}
	// flush logs 滚动 binlog
	if _, err := f.dbWorker.ExecWithTimeout(5*time.Second, "FLUSH LOGS"); err != nil {
		return 0, err
	}
	return f.recover.FilterBinlogFiles()
}

// getBinlogFilesLocal 返回 binlog_dirs 下所有的 binlog 文件名
// 在 WillRecoverBinlog.FilterBinlogFiles 里会掐头去尾
func (f *Flashback) getBinlogFilesLocal() (string, []string, error) {
	// 临时关闭 binlog 删除
	binlogDir, namePrefix, err := f.dbWorker.GetBinlogDir(f.TgtInstance.Port)
	if err != nil {
		return "", nil, err
	} else {
		logger.Info("binlogDir=%s namePrefix=%s", binlogDir, namePrefix)
	}
	files, err := ioutil.ReadDir(binlogDir) // 已经按文件名排序
	if err != nil {
		return "", nil, errors.Wrap(err, "read binlog dir")
	}

	var binlogFiles []string
	reFilename := regexp.MustCompile(cst.ReBinlogFilename)
	for _, fi := range files {
		if !reFilename.MatchString(fi.Name()) {
			if !strings.HasSuffix(fi.Name(), ".index") {
				logger.Warn("illegal binlog file name %s", fi.Name())
			}
			continue
		} else {
			binlogFiles = append(binlogFiles, fi.Name())
		}
	}
	return binlogDir, binlogFiles, nil
}

func (f *Flashback) checkVersionAndVars() error {
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
	flashbackVer80, _ := version.NewVersion("8.0.0")
	fullrowAtLeastVer, _ := version.NewVersion("5.6.24") // 该版本之后才有 binlog_row_image
	if val, err := f.dbWorker.SelectVersion(); err != nil {
		return err
	} else {
		curInstVersion, err := version.NewVersion(val)
		if err != nil {
			return errors.Wrapf(err, "invalid version %s", val)
		}
		if curInstVersion.GreaterThanOrEqual(flashbackVer80) { // 8.0以上要用自己的 mysqlbinlog 版本
			f.ToolSet.Set(tools.ToolMysqlbinlog, f.ToolSet.MustGet(tools.ToolMysqlbinlogRollback80))
			f.recover.ToolSet.Set(tools.ToolMysqlbinlog, f.ToolSet.MustGet(tools.ToolMysqlbinlogRollback80))
		}
		if curInstVersion.LessThan(flashbackAtLeastVer) || curInstVersion.GreaterThan(flashbackVer80) {
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

func (f *Flashback) checkDBTableInUse() error {
	// 检查库是否存在
	var dbTables []native.TableSchema
	if len(f.RecoverOpt.Databases) > 0 && len(f.RecoverOpt.Tables) == 0 {
		for _, db := range f.RecoverOpt.Databases {
			if dbs, err := f.dbWorker.SelectDatabases(db); err != nil {
				return err
			} else if len(dbs) == 0 {
				return errors.Errorf("no databases found for %s", db)
			}
		}
	} else if len(f.RecoverOpt.Databases) > 0 && len(f.RecoverOpt.Tables) > 0 {
		if dbTablesMap, err := f.dbWorker.SelectTables(f.RecoverOpt.Databases, f.RecoverOpt.Tables); err != nil {
			return err
		} else if len(dbTablesMap) == 0 {
			return errors.Errorf("no tables found for %v . %v", f.RecoverOpt.Databases, f.RecoverOpt.Tables)
		} else {
			for _, dbtb := range dbTablesMap {
				dbTables = append(dbTables, dbtb)
			}
		}
	}
	// 检查表是否在使用
	var errList []error
	if openTables, err := f.dbWorker.ShowOpenTables(6 * time.Second); err != nil {
		return err
	} else {
		openTablesList := []string{}
		for _, dbt := range openTables {
			openTablesList = append(openTablesList, fmt.Sprintf("%s.%s", dbt.Database, dbt.Table))
		}
		logger.Info("tables opened %v", openTablesList)
		logger.Info("tables to flashback %+v", dbTables)
		for _, dbt := range dbTables {
			if util.StringsHas(openTablesList, dbt.DBTableStr) {
				errList = append(errList, errors.Errorf("table is opened %s", dbt.DBTableStr))
			}
		}
		if len(errList) > 0 {
			return util.SliceErrorsToError(errList)
		}
	}
	return nil
}

func (f *Flashback) checkTableColumnExists() error {
	return nil
}

func (f *Flashback) checkInstanceSkipped() error {
	return nil
}

func (f *Flashback) checkDBRole() error {
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

func (f *Flashback) checkDiskSpace() error {
	return nil
}
