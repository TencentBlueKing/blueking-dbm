package rollback

import (
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

// FlashbackComp TODO
type FlashbackComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       Flashback                `json:"extend"`
}

// Example TODO
func (c *FlashbackComp) Example() interface{} {
	return FlashbackComp{
		Params: Flashback{
			TargetTime: "2022-11-11 00:00:01",
			StopTime:   "",
			FlashbackBinlog: FlashbackBinlog{
				TgtInstance:      common.InstanceObjExample,
				WorkDir:          "/data/dbbak",
				BinlogDir:        "",
				ParseConcurrency: 2,
				RecoverOpt: &RecoverOpt{
					Databases: []string{"db1", "db2"},
					Tables:    []string{"tb1", "tb2"},
				},
				ToolSet: *tools.NewToolSetWithPickNoValidate(tools.ToolMysqlbinlogRollback),
			},
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
}

// Init TODO
func (f *Flashback) Init() error {
	toolset, err := tools.NewToolSetWithPick(tools.ToolMysqlbinlogRollback, tools.ToolMysqlclient)
	if err != nil {
		return err
	}
	if err = f.ToolSet.Merge(toolset); err != nil {
		return err
	}
	// recover_binlog 用的是 mysqlbinlog, flashback用的是 mysqlbinlog_rollback
	f.ToolSet.Set(tools.ToolMysqlbinlog, f.ToolSet.MustGet(tools.ToolMysqlbinlogRollback))

	f.recover = restore.RecoverBinlog{
		TgtInstance:        f.TgtInstance,
		WorkDir:            f.WorkDir,
		WorkID:             f.WorkID,
		ToolSet:            f.ToolSet,
		QuickMode:          true,
		SourceBinlogFormat: "ROW", // 这里只代表 flashback 要求 ROW 模式，源实例 binlog_format 在 PreCheck 里会判断
		ParseOnly:          true,
		ParseConcurrency:   f.ParseConcurrency,
		RecoverOpt: &restore.MySQLBinlogUtil{
			MySQLClientOpt: &restore.MySQLClientOpt{
				BinaryMode:       true,
				MaxAllowedPacket: 1073741824,
			},
			QueryEventHandler: "error",
			Flashback:         true, // --flashback 模式
			NotWriteBinlog:    false,
			IdempotentMode:    true,
			StartTime:         f.TargetTime,
			Databases:         f.RecoverOpt.Databases,
			Tables:            f.RecoverOpt.Tables,
			DatabasesIgnore:   f.RecoverOpt.DatabasesIgnore,
			TablesIgnore:      f.RecoverOpt.TablesIgnore,
		},
	}
	// 拼接 recover-binlog 参数
	if err := f.recover.Init(); err != nil {
		return err
	}

	f.dbWorker = f.recover.GetDBWorker()
	// 检查起止时间
	dbNowTime, err := f.dbWorker.SelectNow()
	if err != nil {
		return err
	}
	if f.StopTime == "" {
		f.StopTime = dbNowTime
	} else if f.StopTime > dbNowTime {
		return errors.Errorf("StopTime [%s] cannot be greater than db current time [%s]", f.StopTime, dbNowTime)
	}
	f.recover.RecoverOpt.StopTime = f.StopTime

	return nil
}

// downloadBinlogFiles 将文件软连接到 downloadDir
func (f *Flashback) downloadBinlogFiles() error {
	f.binlogSaveDir = filepath.Join(f.recover.GetTaskDir(), "binlog")
	if err := osutil.CheckAndMkdir("", f.binlogSaveDir); err != nil {
		return err
	}
	for _, fn := range f.recover.BinlogFiles {
		srcFile := filepath.Join(f.recover.BinlogDir, fn)
		dstFile := filepath.Join(f.binlogSaveDir, fn)
		if err := osutil.MakeSoftLink(srcFile, dstFile, true); err != nil {
			return errors.Wrap(err, dstFile)
		}
	}
	// 在后续 binlog-recover 环节，使用下载目录
	f.recover.BinlogDir = f.binlogSaveDir
	return nil
}

// PreCheck 检查版本、实例角色、 binlog 格式
// 目前只考虑 binlog 在本地的 flashback，不从远端下载
func (f *Flashback) PreCheck() error {
	var err error
	if err = f.checkVersionAndVars(); err != nil {
		return err
	}
	if err = f.checkDBRole(); err != nil {
		return err
	}
	if err = f.checkDBTableInUse(); err != nil {
		return err
	}
	if f.BinlogDir == "" { // 没有指定 binlog 目录，目前是自动从 实例 binlog 目录本地找，并做软链
		if totalSize, err := f.getBinlogFiles(""); err != nil {
			return err
		} else {
			// 暂定 2 倍 binlog 大小
			diskSizeNeedMB := (totalSize / 1024 / 1024) * 2
			logger.Info("parse binlog need disk size %d MB", diskSizeNeedMB)
		}
		if err = f.downloadBinlogFiles(); err != nil {
			return err
		}
	}

	if err = f.recover.PreCheck(); err != nil {
		return err
	}
	return nil
}

// Start 检查版本、实例角色、 binlog 格式
func (f *Flashback) Start() error {
	if err := f.recover.Start(); err != nil {
		return err
	}
	if err := f.recover.Import(); err != nil {
		return err
	}
	return nil
}
