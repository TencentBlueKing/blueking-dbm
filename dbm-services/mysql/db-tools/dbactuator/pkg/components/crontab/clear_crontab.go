package crontab

import (
	"errors"
	"fmt"
	"os"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
)

// ClearCrontabParam 实际不止这样
type ClearCrontabParam struct {
}

/*
	执行系统初始化脚本 原来的sysinit.sh
	创建mysql账户等操作
*/

// CleanCrontab  注释掉Crontab
//
//	@receiver u
//	@return err
func (u *ClearCrontabParam) CleanCrontab() (err error) {
	logger.Info("开始清理机器上的crontab")
	if err = osutil.CleanLocalCrontab(); err != nil {
		return err
	}

	manager := ma.NewManager("http://127.0.0.1:9999")
	err = manager.Quit()
	if err != nil {
		logger.Error("shutdown mysql-crond failed: %s", err.Error())
	}
	logger.Info("shutdown mysql-crond success")

	return nil
}

// CleanDBToolsFolder 清理相关mysql残留的目录，其中包括
// checksum目录
// dbbackup目录
// rotate_binlog目录
// mysql_crond目录
// dbatools目录
func (u *ClearCrontabParam) CleanDBToolsFolder() (err error) {

	logger.Info("开始删除相关周边组件目录")
	var errList []error
	var isErr bool
	rmList := []string{
		cst.ChecksumInstallPath,
		cst.DbbackupGoInstallPath,
		cst.DBAToolkitPath,
		cst.MySQLCrondInstallPath,
		cst.MysqlRotateBinlogInstallPath,
		cst.MySQLMonitorInstallPath,
		cst.DBAReportBase,
	}
	for _, f := range rmList {
		errList = append(errList, os.RemoveAll(f))
	}

	// 打印所有的err信息
	for _, err := range errList {
		if err != nil && !errors.Is(err, os.ErrNotExist) {
			logger.Error(err.Error())
			isErr = true
		}
	}
	if isErr {
		return fmt.Errorf("clean db-tool-folder failed")
	}
	return nil

}
