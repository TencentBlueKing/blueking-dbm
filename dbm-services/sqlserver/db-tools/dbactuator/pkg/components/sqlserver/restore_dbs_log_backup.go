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

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// RestoreDBSForLogComp 配置
type RestoreDBSForLogComp struct {
	GeneralParam *components.GeneralParam
	Params       *RestoreDBSForLogParam
	RestoreRunTimeCtx
}

// RestoreDBSForLogParam 参数
type RestoreDBSForLogParam struct {
	Host         string           `json:"host" validate:"required,ip" `       // 本地hostip
	Port         int              `json:"port"  validate:"required,gt=0"`     // 需要操作的实例端口
	RestoreInfos []LogRestoreInfo `json:"restore_infos"  validate:"required"` // 需要待恢复备份文件组
	RestoreMode  string           `json:"restore_mode"`                       // 隐藏参数，恢复模式
	RestoreTime  string           `json:"restore_time"`                       // 隐藏参数，恢复指定时间，针对最后一个log文件
}

// RestoreInfo 参数
type LogRestoreInfo struct {
	DBName       string   `json:"db_name" validate:"required" `
	TargetDBName string   `json:"target_db_name"`
	LogBakFiles  []string `json:"bak_file" validate:"required" `
}

// 运行是需要的必须参数,可以提前计算
type RestoreLogRunTimeCtx struct {
	LocalDB     *sqlserver.DbWorker
	VersionYear cst.SQLServerVersionYear
	RestoreMode string
}

// Init 初始化
func (r *RestoreDBSForLogComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
	var version string
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

	if version, err = LWork.GetVersion(); err != nil {
		return fmt.Errorf("get sqlserver version failed ,err:%v", err)
	}
	versionYear, _ := osutil.GetVersionYears(version)

	r.LocalDB = LWork
	r.VersionYear = cst.SQLServerVersionYear(versionYear)
	if r.Params.RestoreMode == "" {
		r.RestoreMode = "RECOVERY"
	} else {
		r.RestoreMode = r.Params.RestoreMode
	}

	return nil
}

// PreCheck 预检测
func (r *RestoreDBSForLogComp) PreCheck() error {
	isError := false
	if len(r.Params.RestoreInfos) == 0 {
		return fmt.Errorf("the file group to be restored is empty, check")
	}
	// 遍历每个文件的本地存在性
	for _, info := range r.Params.RestoreInfos {
		for _, logFile := range info.LogBakFiles {
			f := osutil.WINSFile{FileName: logFile}
			err, check := f.FileExists()
			if err != nil {
				return err
			}
			// 如果文件不存在，则存入error列表，聚合输出
			if !check {
				logger.Error(" database [%s] badkup log file [%s] not exists", info.DBName, logFile)
				isError = true
			}
		}
	}
	if isError {
		return fmt.Errorf("check backup-log-files is failed")
	}
	return nil
}

// DoRestoreForFullBackup 做日志备份的恢复
func (r *RestoreDBSForLogComp) DoRestoreForLogBackup() error {
	var isGlobalErr bool
	for _, info := range r.Params.RestoreInfos {
		var dbState string
		var restoreLogState bool
		// 恢复日志
		for i, logFile := range info.LogBakFiles {
			var fileRestoreMode string
			var restoreTime string
			// 拼接恢复SQL，执行, 如果不是最后一个log file，每次恢复都传NORECOVERY
			if i == len(info.LogBakFiles)-1 {
				fileRestoreMode = r.RestoreMode
				restoreTime = r.Params.RestoreTime
			} else {
				fileRestoreMode = "NORECOVERY"
				restoreTime = ""
			}
			if err := r.LocalDB.DBRestoreForLogBackup(
				info.TargetDBName,
				logFile,
				fileRestoreMode,
				restoreTime); err != nil {
				logger.Error("restroe log [%s] in db [%s] error : [%v]", logFile, info.TargetDBName, err)
				isGlobalErr = true
				restoreLogState = true
				continue
			}
		}

		if restoreLogState {
			continue
		}

		// 需要检查一下DB的状态是否恢复成功,确保DB正常访问
		checkCmd := fmt.Sprintf("select state_desc from master.sys.databases where name = '%s'", info.TargetDBName)
		if err := r.LocalDB.Queryxs(&dbState, checkCmd); err != nil {
			logger.Error("check db[%s] state is error : [%s]", info.TargetDBName, err.Error())
			isGlobalErr = true
			continue
		}
		if r.RestoreMode == "RECOVERY" && dbState != "ONLINE" {
			//指定恢复DB时，状态不是不是online，则报异常
			logger.Error(
				"DB[%s] state is not online after recovery marked RECOVERY, check. dbState:[%s]",
				info.TargetDBName,
				dbState,
			)
			isGlobalErr = true
		}

	}
	if isGlobalErr {
		return fmt.Errorf("restore-log error")
	}

	return nil
}
