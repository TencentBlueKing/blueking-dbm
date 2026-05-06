package mysql

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/backupdemand"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"slices"
)

type DumpPrivComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	backupdemand.Component
	Params *DumpPrivParam `json:"extend"`
}

type DumpPrivParam struct {
	backupdemand.Param
	SourcePrivFilePath string `json:"source_priv_file_path"`
}

func (c *DumpPrivComponent) Init() error {
	logger.Info("params: %v", c.Params)
	c.Component.Params = &c.Params.Param
	c.Component.GeneralParam = c.GeneralParam
	return c.Component.Init()
}

func (c *DumpPrivComponent) RenamePrivFile() error {
	report, _, err := c.GenerateReport()
	if err != nil {
		logger.Error("generating report failed: %s", err.Error())
		return err
	}

	b, err := json.Marshal(*report)
	if err != nil {
		logger.Error("report json marshal failed: %s", err.Error())
		return err
	}
	logger.Info("report content: %s", string(b))

	idx := slices.IndexFunc(
		report.Result.FileList, func(ele *dbareport.TarFileItem) bool {
			return ele.FileType == "priv"
		},
	)
	if idx < 0 {
		err := fmt.Errorf("priv file not found")
		logger.Error(err.Error())
		return err
	}

	privFileItem := report.Result.FileList[idx]
	//if privFileItem.ContainFiles == nil {
	//	err := fmt.Errorf("priv file does not contain any files")
	//	logger.Error(err.Error())
	//	return err
	//}
	//if len(privFileItem.ContainFiles) > 1 {
	//	err := fmt.Errorf("priv file contains more than one file: %v", privFileItem.ContainFiles)
	//	logger.Error(err.Error())
	//	return err
	//}

	privFilePath := filepath.Join(report.Result.OriginalBackupDir, privFileItem.FileName)

	// 把权限备份文件复制一份
	src, err := os.Open(privFilePath)
	if err != nil {
		logger.Error("open priv file %s err: %v", privFilePath, err)
		return err
	}
	defer func() {
		_ = src.Close()
	}()

	dst, err := os.Create(c.Params.SourcePrivFilePath)
	if err != nil {
		logger.Error("create copy file %s err: %v", c.Params.SourcePrivFilePath, err)
		return err
	}
	defer func() {
		_ = dst.Close()
	}()

	if _, err := io.Copy(dst, src); err != nil {
		logger.Error("copy file from %s to %s err: %v", privFilePath, c.Params.SourcePrivFilePath, err)
		return err
	}

	logger.Info("copied priv file from %s to %s", privFilePath, c.Params.SourcePrivFilePath)
	return nil
}
