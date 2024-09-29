/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// InitSqlserverInstanceComp 克隆用户权限
type InitSqlserverInstanceComp struct {
	GeneralParam *components.GeneralParam
	Params       *InitSqlserverInstanceParam
	initrunTimeCtx
}

// InitSqlserverInstanceParam 参数
type InitSqlserverInstanceParam struct {
	Host string `json:"host" validate:"required,ip" `   // 本地hostip
	Port int    `json:"port"  validate:"required,gt=0"` // 需要操作的实例端口

}

// initrunTimeCtx 上下文
type initrunTimeCtx struct {
	DB              *sqlserver.DbWorker
	DRS             []slaves
	BackupFilter    []string
	MirroringFilter []string
	BackupConfigs   []BackupConfig
	SqlserverVerion string
	IsSysDBExist    bool
}

type BackupConfig struct {
	FullBackupPath     string `db:"FULL_BACKUP_PATH"`
	LogBackupPath      string `db:"LOG_BACKUP_PATH"`
	KeepFullBackupDays string `db:"KEEP_FULL_BACKUP_DAYS"`
	KeepLogBackupDays  string `db:"KEEP_LOG_BACKUP_DAYS"`
}

// Init初始化
func (r *InitSqlserverInstanceComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
	var sql string = fmt.Sprintf("select count(0) as cnt from master.sys.databases where name = '%s';", cst.SysDB)
	var cnt int
	// 初始化本地实例连接
	if LWork, err = sqlserver.NewDbWorker(
		r.GeneralParam.RuntimeAccountParam.SAUser,
		r.GeneralParam.RuntimeAccountParam.SAPwd,
		r.Params.Host,
		r.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			r.Params.Host, r.Params.Port, err.Error())
		return err
	}
	r.DB = LWork
	// 获取实例版本
	if r.SqlserverVerion, err = r.DB.GetVersion(); err != nil {
		return err
	}
	// 判断是否存在系统库
	if err := r.DB.Queryxs(&cnt, sql); err != nil {
		return fmt.Errorf("check-db failed:%v", err)

	}
	if cnt != 0 {
		// 代表DB存在
		r.IsSysDBExist = true
	}
	return nil
}

// CreateSysUser 创建系统账号
func (r *InitSqlserverInstanceComp) CreateSysUser() error {
	// 初始化admin账号
	if err := r.DB.CreateLoginUser(
		r.GeneralParam.RuntimeAccountParam.MssqlAdminUser,
		r.GeneralParam.RuntimeAccountParam.MssqlAdminPwd,
		"sysadmin",
	); err != nil {
		logger.Error("init admin login failed %v", err)
		return err
	}
	// 初始化drs账号
	if err := r.DB.CreateLoginUser(
		r.GeneralParam.RuntimeAccountParam.DRSUser,
		r.GeneralParam.RuntimeAccountParam.DRSPwd,
		"sysadmin",
	); err != nil {
		logger.Error("init drs login failed %v", err)
		return err
	}
	// 初始化dbha账号
	if err := r.DB.CreateLoginUser(
		r.GeneralParam.RuntimeAccountParam.DBHAUser,
		r.GeneralParam.RuntimeAccountParam.DBHAPwd,
		"sysadmin",
	); err != nil {
		logger.Error("init dbha login failed %v", err)
		return err
	}

	// 初始化mssql_exporter账号
	if err := r.DB.CreateLoginUser(
		r.GeneralParam.RuntimeAccountParam.MssqlExporterUser,
		r.GeneralParam.RuntimeAccountParam.MssqlExporterPwd,
		"public",
	); err != nil {
		logger.Error("init mssql_exporter failed %v", err)
		return err
	}
	// mssql_exporter账号, 授权
	exporterCmd := fmt.Sprintf(
		cst.GRANT_MSSQL_EXPORTER_SQL,
		r.GeneralParam.RuntimeAccountParam.MssqlExporterUser,
	)
	if _, err := r.DB.Exec(exporterCmd); err != nil {
		logger.Error("init mssql_exporter-grant failed %v", err)
		return err
	}
	return nil
}

// ExportInstanceConf 生成exporter配置
func (r *InitSqlserverInstanceComp) CreateExporterConf() error {
	dir := osutil.WINSFile{FileName: filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_EXPOTER_NAME)}
	err, check := dir.FileExists()
	if err != nil {
		// 表示检查目录是否存在出现异常，报错
		return err
	}
	if !check {
		// 表示目录在系统不存在，创建
		if !dir.Create(0777) {
			return fmt.Errorf("create dir [%s] failed", dir.FileName)
		}
		logger.Info("create system-dir [%s] successfully", dir.FileName)

	}

	if err := osutil.CreateExporterConf(
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_EXPOTER_NAME, fmt.Sprintf("exporter_%d.conf", r.Params.Port)),
		"localhost",
		r.Params.Port,
		r.GeneralParam.RuntimeAccountParam.MssqlExporterUser,
		r.GeneralParam.RuntimeAccountParam.MssqlExporterPwd,
	); err != nil {
		return err
	}
	return nil
}

// ExportInstanceConf 导出系统库配置
func (r *InitSqlserverInstanceComp) ExportInstanceConf() error {
	// 检测系统库是否存在
	if !r.IsSysDBExist {
		logger.Warn(fmt.Sprintf("%s is not exist, skip", cst.SysDB))
		return nil
	}
	// 查询backup_filter
	if err := r.DB.Queryx(&r.BackupFilter, fmt.Sprintf(cst.BACKUP_FILTER_SQL, cst.SysDB)); err != nil {
		logger.Error("check backup_filter_table failed: %v", err)
	}
	// 查询mirroring_filter
	if err := r.DB.Queryx(&r.MirroringFilter, fmt.Sprintf(cst.MIORRING_FILTER_SQL, cst.SysDB)); err != nil {
		logger.Error("check mirroring_filter_table failed: %v", err)
	}
	// 查询backup_settings
	if err := r.DB.Queryx(&r.BackupConfigs, fmt.Sprintf(cst.BACKUP_SETTING_SQL, cst.SysDB)); err != nil {
		logger.Error("check backup_settings_table failed: %v", err)
	}
	return nil

}

// InitMoitorDB 初始化系统库
func (r *InitSqlserverInstanceComp) InitSysDB() error {
	var files []string
	var err error
	if files, err = WriteInitSQLFile(); err != nil {
		return err
	}
	if err := sqlserver.ExecLocalSQLFile(r.SqlserverVerion, "master", 0, files, r.Params.Port); err != nil {
		return err
	}
	// 继承相关配置
	if len(r.BackupFilter) == 0 {
		insertBackupFilterSQL := fmt.Sprintf(
			"insert into [%s].[dbo].[BACKUP_FILTER] values ('%s')",
			cst.SysDB,
			strings.Join(r.BackupFilter, "','"),
		)
		if _, err := r.DB.Exec(insertBackupFilterSQL); err != nil {
			return err
		}
	}
	if len(r.MirroringFilter) == 0 {
		insertMirroringFilterSQL := fmt.Sprintf(
			"insert into [%s].[dbo].[MIRRORING_FILTER] values ('%s')",
			cst.SysDB,
			strings.Join(r.MirroringFilter, "','"),
		)
		if _, err := r.DB.Exec(insertMirroringFilterSQL); err != nil {
			return err
		}

	}
	return nil
}

// PrintBackupCtx 保存原本备份配置，提供下一个节点使用
func (r *InitSqlserverInstanceComp) PrintBackupConfig() error {

	// 重建临时表
	sqlFile := staticembed.CreateBackupOldTable
	data, err := staticembed.SQLScript.ReadFile(sqlFile)
	if err != nil {
		return fmt.Errorf("read sql script failed %s", err.Error())
	}
	// 添加 UTF-8 BOM 字节序列
	data = append([]byte{0xEF, 0xBB, 0xBF}, data...)

	tmpScriptName := filepath.Join(cst.BASE_DATA_PATH, sqlFile)
	if err = os.WriteFile(tmpScriptName, data, 0755); err != nil {
		logger.Error("write sql script failed %s", err.Error())
		return err
	}
	// 执行
	if err := sqlserver.ExecLocalSQLFile(
		r.SqlserverVerion, cst.SysDB, 0, []string{tmpScriptName}, r.Params.Port,
	); err != nil {
		return err
	}

	// 在这里判断是否有旧备份配置，是为了统一用BACKUP_SETTING_OLD表，下个节点号判断
	if len(r.BackupConfigs) == 0 {
		// 表示配置为空，直接跳过
		logger.Warn("old backup config is null, skip")

	} else {
		// 导入
		insertSql := fmt.Sprintf(
			`insert into [%s].[dbo].[BACKUP_SETTING_OLD] (
				FULL_BACKUP_PATH, 
				LOG_BACKUP_PATH, 
				KEEP_FULL_BACKUP_DAYS, 
				KEEP_LOG_BACKUP_DAYS
			) values('%s','%s','%s','%s');`,
			cst.SysDB,
			r.BackupConfigs[0].FullBackupPath,
			r.BackupConfigs[0].LogBackupPath,
			r.BackupConfigs[0].KeepFullBackupDays,
			r.BackupConfigs[0].KeepLogBackupDays,
		)
		if _, err := r.DB.Exec(insertSql); err != nil {
			return err
		}
	}

	// 执行完成后删除文件,删除失败不退出
	remoteCmd := fmt.Sprintf("REMOVE-ITEM %s", sqlFile)
	if _, err := osutil.StandardPowerShellCommand(remoteCmd); err != nil {
		logger.Warn("delete [%s] failed %s", sqlFile, err.Error())
	}

	return nil
}

// CreateSysDir TODO
func (r *InitSqlserverInstanceComp) CreateSysDir() error {
	logger.Info("start exec createSysDir ...")
	createDir := []string{
		filepath.Join(cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_DATA_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.IEOD_FILE_BACKUP),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_EXPOTER_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_DBHA_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME, "full"),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME, "log"),
	}
	// 判断机器是否存在E盘，如果有在创建必要目录
	e := osutil.WINSFile{FileName: cst.BASE_BACKUP_PATH}
	err, check := e.FileExists()
	if err != nil {
		logger.Warn(err.Error())
	}
	if check {
		// 添加E盘必须创建的目录
		createDir = append(createDir, filepath.Join(cst.BASE_DATA_PATH, cst.BASE_BACKUP_PATH))
		createDir = append(createDir, filepath.Join(cst.BASE_DATA_PATH, cst.BASE_BACKUP_PATH, "full"))
		createDir = append(createDir, filepath.Join(cst.BASE_DATA_PATH, cst.BASE_BACKUP_PATH, "log"))
	}

	// 循环创建目录
	for _, dirName := range createDir {
		dir := osutil.WINSFile{FileName: dirName}
		err, check := dir.FileExists()
		if check && err == nil {
			// 表示目录在系统存在，先跳过
			continue
		}
		if err != nil {
			// 表示检查目录是否存在出现异常，报错
			return err
		}
		// 创建目录
		if !dir.Create(0777) {
			return fmt.Errorf("create dir [%s] failed", dirName)
		}
		logger.Info("create system-dir [%s] successfully", dirName)
	}
	// 增加一个cygwin目录，目的让备份系统可以顺利下载文件
	cygwinHomeDir := osutil.WINSFile{FileName: cst.CYGWIN_MSSQL_PATH}
	_, cygwinHomecheck := cygwinHomeDir.FileExists()
	if cygwinHomecheck {
		// 表示目录在系统存在，跳过
		return nil
	}
	// 创建mssql目录，不捕捉日志
	cygwinHomeDir.Create(0777)
	return nil
}
