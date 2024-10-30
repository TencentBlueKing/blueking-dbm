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
	"path/filepath"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

var FULL_BACKUP = "full_backup"
var LOG_BACKUP = "log_backup"

// BackupDBSComp 备份数据库,支持全量备份和日志备份
type BackupDBSComp struct {
	GeneralParam *components.GeneralParam
	Params       *BackupDBSParam
	backupRunTimeCtx
}

// BackupDBSParam 参数
type BackupDBSParam struct {
	Host            string   `json:"host" validate:"required,ip" `     // 本地hostip
	Port            int      `json:"port"  validate:"required,gt=0"`   // 需要操作的实例端口
	BackupDBS       []string `json:"backup_dbs"  validate:"required"`  // 备份库表的传入列表
	JobID           string   `json:"job_id"  validate:"required"`      // 备份单据ID
	BackupType      string   `json:"backup_type"  validate:"required"` // 备份类型
	FileTag         string   `json:"file_tag"  validate:"required"`    // 备份文件存储类型
	IsSetFullModel  bool     `json:"is_set_full_model"`                // 隐藏参数，是否数据库强制设置成full模式
	TargetBackupDir string   `json:"target_backup_dir"`                // 隐藏参数，指定备份文件位置
}

// 运行是需要的必须参数,可以提前计算
type backupRunTimeCtx struct {
	LocalDB   *sqlserver.DbWorker
	RealDBS   []string
	BackupDir string
	BackupID  string
}

// Init 初始化
func (b *BackupDBSComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
	if LWork, err = sqlserver.NewDbWorker(
		b.GeneralParam.RuntimeAccountParam.SAUser,
		b.GeneralParam.RuntimeAccountParam.SAPwd,
		b.Params.Host,
		b.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			b.Params.Host, b.Params.Port, err.Error())
		return err
	}
	b.LocalDB = LWork

	// 计算需要备份的db列表
	if err := b.GetRealDBS(); err != nil {
		return err
	}
	logger.Info("real dbs: %v", b.RealDBS)

	// 计算当前备份的本地目录
	if b.Params.TargetBackupDir != "" {
		b.BackupDir = b.Params.TargetBackupDir
	} else {
		b.BackupDir = filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME, b.Params.JobID)
	}
	// 计算这次的backup_job_id
	b.BackupID = osutil.GenerateRandomString(32)

	// 创建备份目录
	dir := osutil.WINSFile{FileName: b.BackupDir}
	err, check := dir.FileExists()
	if check && err == nil {
		// 表示目录在系统存在，先跳过
		logger.Info(fmt.Sprintf("backup-dir [%s] exist", b.BackupDir))
		return nil
	}
	if err != nil {
		// 表示检查目录是否存在出现异常，报错
		return err
	}
	// 创建目录
	if !dir.Create(0777) {
		return fmt.Errorf("create backup-dir [%s] failed", b.BackupDir)
	}
	logger.Info("create backup-dir [%s] successfully", b.BackupDir)
	return nil
}

// GetRealDBS todo
func (b *BackupDBSComp) GetRealDBS() error {
	for _, dbName := range b.Params.BackupDBS {
		// 判断db是否还存在
		var sql string = "select count(0) as cnt from master.sys.databases where name = '%s';"
		var cnt int
		checkDBSQL := fmt.Sprintf(sql, dbName)
		if err := b.LocalDB.Queryxs(&cnt, checkDBSQL); err != nil {
			return fmt.Errorf("check-db failed:%v", err)
		}
		if cnt == 0 {
			// 代表DB不存在
			logger.Warn("[%s] DB not exists,skip", dbName)
			continue
		}
		// 没有报错则加入待重命名数组
		logger.Info("the db [%s] enters the backup queue", dbName)
		b.RealDBS = append(b.RealDBS, dbName)
	}

	if len(b.RealDBS) == 0 {
		// 空代表无匹配需要备份的DB, 异常退出
		return fmt.Errorf("cannot match DB, check: BackupDBS=[%v]", b.Params.BackupDBS)
	}
	return nil
}

// DoDackup todo
func (b *BackupDBSComp) DoDackup() error {
	switch b.Params.BackupType {
	case FULL_BACKUP:
		return b.DoFullDackup()
	case LOG_BACKUP:
		return b.DoLogDackup()
	default:
		return fmt.Errorf("backup type [%s] is not supported", b.Params.BackupType)
	}
}

// DoFullDackup 执行备份指令,完整备份
func (b *BackupDBSComp) DoFullDackup() error {
	var errInfos []string
	var execCmds []string
	// 返回dblist 为空， 直接退出
	if len(b.RealDBS) == 0 {
		return nil
	}

	for _, dbName := range b.RealDBS {
		var dbRecoveryModel int

		// 查询db模式
		checkRecoveryModelSql := fmt.Sprintf(
			"select recovery_model from master.sys.databases where name = '%s';", dbName,
		)
		// 查询失败报错
		if err := b.LocalDB.Queryxs(&dbRecoveryModel, checkRecoveryModelSql); err != nil {
			errInfos = append(errInfos, fmt.Sprintf("check recovery failed %v", err))
			continue
		}
		if dbRecoveryModel != 1 && b.Params.IsSetFullModel {
			// 强制降备份库改成full模式
			execCmds = append(execCmds, fmt.Sprintf("ALTER DATABASE [%s] SET RECOVERY FULL WITH NO_WAIT;", dbName))
		}
	}
	// 生成备份数据库命令
	execCmds = append(
		execCmds,
		fmt.Sprintf("EXEC MONITOR.DBO.TOOL_BACKUP_DATABASE 1,'%s','%s','%s\\','%s'",
			b.BackupID, strings.Join(b.RealDBS, ","), b.BackupDir, b.Params.FileTag),
	)

	if len(errInfos) != 0 {
		return fmt.Errorf("%v", errInfos)
	}
	// 执行备份命令组
	logger.Info("exec backup sql:[%v]", execCmds)
	if _, err := b.LocalDB.ExecMore(execCmds); err != nil {
		logger.Error("backup database failed %v", err)
		return err
	}

	return nil
}

// DoDackup 执行备份指令,日志备份
func (b *BackupDBSComp) DoLogDackup() error {
	var errInfos []string
	var execCmds []string
	// 返回dblist 为空， 直接退出
	if len(b.RealDBS) == 0 {
		return nil
	}
	for _, dbName := range b.RealDBS {
		var dbRecoveryModel int

		// 查询db模式
		checkRecoveryModelSql := fmt.Sprintf(
			"select recovery_model from master.sys.databases where name = '%s';", dbName,
		)
		// 查询失败报错
		if err := b.LocalDB.Queryxs(&dbRecoveryModel, checkRecoveryModelSql); err != nil {
			errInfos = append(errInfos, fmt.Sprintf("check recovery failed %v", err))
			continue
		}
		// 判断是否生成数据库LOG备份命令
		if dbRecoveryModel != 1 {
			errInfos = append(errInfos, fmt.Sprintf("db [%s] is not in full mode [%d]", dbName, dbRecoveryModel))
			continue
		}
	}

	execCmds = append(
		execCmds,
		fmt.Sprintf("EXEC MONITOR.DBO.TOOL_BACKUP_DATABASE 2,'%s','%s','%s\\','%s'",
			b.BackupID, strings.Join(b.RealDBS, ","), b.BackupDir, b.Params.FileTag),
	)

	if len(errInfos) != 0 {
		return fmt.Errorf("%v", errInfos)
	}

	// 执行备份命令组
	logger.Info("exec backup sql:[%v]", execCmds)
	if _, err := b.LocalDB.ExecMore(execCmds); err != nil {
		logger.Error("backup log failed %v", err)
		return err
	}

	return nil

}

// checkBackupSuccess 检测这次备份的文件是否有缺失的情况
func (b *BackupDBSComp) CheckBackupSuccess() error {
	// 根据产生的backupid 以及 db名称去获取到对应的备份文件名称，然后判断文件是否存在
	var errInfos []string
	for _, dbName := range b.RealDBS {
		var fileName string
		checkSQL := fmt.Sprintf(
			"select top(1) filename from [%s].[dbo].[BACKUP_TRACE] where BACKUP_ID = '%s' and DBNAME = '%s' ",
			cst.SysDB,
			b.BackupID,
			dbName,
		)
		if err := b.LocalDB.Queryxs(&fileName, checkSQL); err != nil {
			errInfos = append(errInfos, fmt.Sprintf("check db-backupfile [%s] failed %v", dbName, err))
			continue
		}
		// 如果返回为空，则证明db备份失败
		if fileName == "" {
			errInfos = append(errInfos, fmt.Sprintf("This db [%s] backup record does not exist", dbName))
			continue
		}
		// 判断备份文件是否存在
		file := filepath.Join(b.BackupDir, fileName)
		f := osutil.WINSFile{FileName: file}
		err, check := f.FileExists()
		if check && err == nil {
			// 表示文件在系统存在
			continue
		} else {
			errInfos = append(
				errInfos,
				fmt.Sprintf("This db [%s] backup file [%s] does not exist: check[%t]; err:[%v]",
					dbName, file, check, err),
			)
			continue
		}
	}
	if len(errInfos) != 0 {
		return fmt.Errorf("%v", errInfos)
	}
	return nil
}

// 成功输出backup_id
func (b *BackupDBSComp) PrintBackupID() error {
	components.WrapperOutputString(fmt.Sprintf("{\"id\": \"%s\"}", b.BackupID))
	return nil
}
