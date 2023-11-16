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
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// BackupDBSComp 备份数据库
type BackupDBSComp struct {
	GeneralParam *components.GeneralParam
	Params       *BackupDBSParam
	backupRunTimeCtx
}

// BackupDBSParam 参数
type BackupDBSParam struct {
	Host           string `json:"host" validate:"required,ip" `          // 本地hostip
	Port           int    `json:"port"  validate:"required,gt=0"`        // 需要操作的实例端口
	BackupDBSRegex string `json:"backup_dbs_regex"  validate:"required"` // 备份库表的
	IngoreDBSregex string `json:"ingore_dbs_regex"  validate:"required"`
	BackupID       string `json:"backup_id"  validate:"required"`
}

// 运行是需要的必须参数,可以提前计算
type backupRunTimeCtx struct {
	LocalDB   *sqlserver.DbWorker
	RealDBS   []string
	BackupDir string
}

// 定义备份信息的结构体
type BackupInfo struct {
	DBName     string
	BakFiles   []string
	BackupType string
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
	return nil
}

// GetRealDBS todo
func (b *BackupDBSComp) GetRealDBS() error {
	checkCmd := cst.GET_BUSINESS_DATABASE
	if b.Params.BackupDBSRegex == b.Params.IngoreDBSregex {
		// 过滤正则和 忽略正则一致时，直接报错
		return fmt.Errorf(
			"backupDBSRegex [%s] and IngoreDBSregex [%s] "+
				" have the same configuration and cannot filter out the data list",
			b.Params.BackupDBSRegex,
			b.Params.IngoreDBSregex,
		)
	}
	if b.Params.IngoreDBSregex == "*" {
		// 如果忽略正则是全匹配，直接报错
		return fmt.Errorf(
			" ingoreDBSregex [%s] cannot filter out the data list",
			b.Params.IngoreDBSregex,
		)

	}
	// 拼接sqlserver支持的正则语法
	if strings.Contains(b.Params.BackupDBSRegex, "%") {
		checkCmd = checkCmd + fmt.Sprintf(" and name like '%s'", b.Params.BackupDBSRegex)
	}
	if strings.Contains(b.Params.BackupDBSRegex, "?") {
		newRegex := strings.ReplaceAll(b.Params.BackupDBSRegex, "?", "_")
		checkCmd = checkCmd + fmt.Sprintf(" and name like '%s'", newRegex)
	}
	if strings.Contains(b.Params.IngoreDBSregex, "%") {
		checkCmd = checkCmd + fmt.Sprintf(" and name not like '%s'", b.Params.IngoreDBSregex)
	}
	if strings.Contains(b.Params.IngoreDBSregex, "?") {
		newRegex := strings.ReplaceAll(b.Params.IngoreDBSregex, "?", "_")
		checkCmd = checkCmd + fmt.Sprintf(" and name  not like '%s'", newRegex)
	}
	// 执行查询要备份的DB list
	if err := b.LocalDB.Queryxs(&b.RealDBS, checkCmd); err != nil {
		return fmt.Errorf("get db list failed %v", err)
	}
	if len(b.RealDBS) == 0 {
		// 空代表无匹配需要备份的DB, 但不做异常退出
		logger.Warn(
			"cannot match DB, check : BackupDBSRegex [%s] , IngoreDBSregex [%s]",
			b.Params.BackupDBSRegex,
			b.Params.IngoreDBSregex,
		)
		return nil
	}
	// 计算当前备份的本地目录
	b.BackupDir = fmt.Sprintf("%s%s\\%s",
		cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME, b.Params.BackupID)
	return nil
}

// DoDackup 执行备份指令
func (b *BackupDBSComp) DoDackup() error {
	// 返回dblist 为空， 直接退出
	if len(b.RealDBS) == 0 {
		return nil
	}

	for _, dbName := range b.RealDBS {
		bakFile := fmt.Sprintf("%s\\%s.bak", b.BackupDir, dbName)
		trnFile := fmt.Sprintf("%s\\%s.trn", b.BackupDir, dbName)
		execCmds := []string{
			fmt.Sprintf("ALTER DATABASE [%s] SET RECOVERY FULL WITH NO_WAIT", dbName),
			fmt.Sprintf("BACKUP DATABASE [%s] TO DISK='%s' with init", dbName, bakFile),
			fmt.Sprintf("BACKUP LOG [%s] TO DISK='%s' with init", dbName, trnFile),
		}
		if _, err := b.LocalDB.ExecMore(execCmds); err != nil {
			logger.Error("backup database [%s] failed %v", dbName, err)
			return err
		}

	}

	return nil
}
