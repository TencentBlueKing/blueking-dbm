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
	"database/sql"
	"fmt"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// RestoreDBSForFullComp 配置
type RestoreDBSForFullComp struct {
	GeneralParam *components.GeneralParam
	Params       *RestoreDBSForFullParam
	RestoreRunTimeCtx
}

// RestoreDBSForFullParam 参数
type RestoreDBSForFullParam struct {
	Host         string            `json:"host" validate:"required,ip" `       // 本地hostip
	Port         int               `json:"port"  validate:"required,gt=0"`     // 需要操作的实例端口
	RestoreInfos []FullRestoreInfo `json:"restore_infos"  validate:"required"` // 需要待恢复备份文件组
	RestoreMode  string            `json:"restore_mode"`                       // 隐藏参数，恢复模式
}

// RestoreInfo 参数
type FullRestoreInfo struct {
	DBName       string `json:"db_name" validate:"required" `
	TargetDBName string `json:"target_db_name"`
	FullBakFile  string `json:"bak_file" validate:"required" `
}

// FullBackupHeaderInfo todo
type FullBackupHeaderInfo struct {
	DatabaseName       string `db:"DatabaseName"`
	BackupType         string `db:"BackupType"`
	BackupSize         string `db:"BackupSize"`
	Compressed         string `db:"Compressed"`
	CompatibilityLevel int    `db:"CompatibilityLevel"`
}

// FullBackupListInfo todo
type FullBackupListInfo struct {
	LogicalName   string         `db:"LogicalName"`
	PhysicalName  string         `db:"PhysicalName"`
	Type          string         `db:"Type"`
	FileGroupName sql.NullString `db:"FileGroupName"`
}

// 运行是需要的必须参数,可以提前计算
type RestoreRunTimeCtx struct {
	LocalDB     *sqlserver.DbWorker
	VersionYear cst.SQLServerVersionYear
	RestoreMode string
}

// Init 初始化
func (r *RestoreDBSForFullComp) Init() error {
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
func (r *RestoreDBSForFullComp) PreCheck() error {
	isError := false
	if len(r.Params.RestoreInfos) == 0 {
		return fmt.Errorf("the file group to be restored is empty, check")
	}
	// 遍历每个文件的本地存在性
	for _, info := range r.Params.RestoreInfos {

		f := osutil.WINSFile{FileName: info.FullBakFile}
		err, check := f.FileExists()
		if err != nil {
			return err
		}
		// 如果文件不存在，则存入error列表，聚合输出
		if !check {
			logger.Error(" database [%s] badkup dir [%s] not exists", info.DBName, info.FullBakFile)
			isError = true
		}

	}
	if isError {
		return fmt.Errorf("check backup-files is failed")
	}
	if err := r.CheckRestoreReasonableness(); err != nil {
		return err
	}
	return nil
}

// CheckRestoreReasonableness 检测恢复备份文件组合法性
// 合法性包括：
// 1: 判断备份文件是否传入数据库名称统一
// 2: 备份文件是否可以支持恢复
func (r *RestoreDBSForFullComp) CheckRestoreReasonableness() error {
	var isErr bool
	for _, info := range r.Params.RestoreInfos {

		var infoArr []FullBackupHeaderInfo
		checkSQL := fmt.Sprintf("RESTORE HEADERONLY FROM DISK = '%s'", info.FullBakFile)
		// 查询失败报错
		if err := r.LocalDB.Queryx(&infoArr, checkSQL); err != nil {
			logger.Error("check db %s failed: %v", info.DBName, err)
			isErr = true
		}
		// 判断备份文件是否传入数据库名称是否统一
		if infoArr[0].DatabaseName != info.DBName {
			logger.Error("not a backup [%s] of this database [%s]", info.FullBakFile, info.DBName)
			isErr = true
		}
		// 备份文件是否可以支持恢复
		if !slices.Contains(
			cst.CompatibilityLevelMap[r.VersionYear],
			infoArr[0].CompatibilityLevel,
		) {
			logger.Error(
				"backup-CompatibilityLevel [%d]  does not support recovery in this database system [%d]",
				infoArr[0].CompatibilityLevel,
				r.VersionYear,
			)
			isErr = true
		}

	}
	if isErr {
		return fmt.Errorf("check error")
	}

	return nil
}

// DoRestoreForFullBackup 做全量备份的恢复
func (r *RestoreDBSForFullComp) DoRestoreForFullBackup() error {
	var isGlobalErr bool
	for _, info := range r.Params.RestoreInfos {
		var isErr bool
		var moveSQLs []string
		var infoArr []FullBackupListInfo
		checkSQL := fmt.Sprintf("restore filelistonly from disk='%s';", info.FullBakFile)
		// 查询失败报错
		if err := r.LocalDB.Queryx(&infoArr, checkSQL); err != nil {
			logger.Error("check db %s failed: %v", info.DBName, err)
			isGlobalErr = true
			isErr = true
		}
		// 如果在内层循环出错，则无需往下执行，跳过
		if isErr {
			continue
		}
		for _, f := range infoArr {
			randStr := osutil.GenerateRandomString(8)
			newFileName := ""

			directory := filepath.Dir(f.PhysicalName)
			// 判断对应恢复的目录存不存在，如果不存在，则默认存在D:\gamedb\{port}
			dir := osutil.WINSFile{FileName: directory}
			err, check := dir.FileExists()
			if err != nil {
				return err
			}
			// 如果文件不存在
			if !check {
				logger.Warn("the folder is not exist, restore dir set D:\\gamedb\\%d", r.Params.Port)
				directory = filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_DATA_NAME, strconv.Itoa(r.Params.Port))
			}

			switch {
			case f.FileGroupName.String == "PRIMARY" && f.Type == "D":
				// 代表是主文件组，默认就有
				newFileName = filepath.Join(directory, fmt.Sprintf("%s_%s.mdf", info.DBName, randStr))
			case f.FileGroupName.String != "PRIMARY" && f.Type == "D":
				// 代表是辅助文件组，可选
				newFileName = filepath.Join(directory, fmt.Sprintf("%s_%s.ndf", info.DBName, randStr))
			case f.Type == "L":
				// 代表是日志文件组，默认就有
				newFileName = filepath.Join(directory, fmt.Sprintf("%s_%s.ldf", info.DBName, randStr))
			default:
				logger.Error(
					"[%s] this FileGroupName [%s] and Type [%s] is not supported",
					info.DBName,
					f.FileGroupName.String,
					f.Type,
				)
				isErr = true
			}
			// 检测到文件组类型不符合，则退出这次的内层遍历
			if isErr {
				break
			}
			moveSQLs = append(moveSQLs, fmt.Sprintf("move '%s' to '%s'", f.LogicalName, newFileName))

		}
		// 如果在内层循环出错，则无需往下执行，跳过
		if isErr {
			continue
		}

		// 拼接恢复SQL，执行
		if err := r.LocalDB.DBRestoreForFullBackup(
			info.TargetDBName,
			info.FullBakFile,
			strings.Join(moveSQLs, ","),
			r.RestoreMode); err != nil {
			logger.Error("restroe db [%s->%s] error : [%v]", info.DBName, info.TargetDBName, err)
			isGlobalErr = true
		}
	}
	if isGlobalErr {
		return fmt.Errorf("restore-full-dbs error")
	}

	return nil
}
