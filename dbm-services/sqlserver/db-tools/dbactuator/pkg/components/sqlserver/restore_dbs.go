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
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// RestoreDBSComp 克隆用户权限
type RestoreDBSComp struct {
	GeneralParam *components.GeneralParam
	Params       *RestoreDBSParam
	RestoreRunTimeCtx
}

// RestoreDBSParam 参数
type RestoreDBSParam struct {
	Host         string       `json:"host" validate:"required,ip" `       // 本地hostip
	Port         int          `json:"port"  validate:"required,gt=0"`     // 需要操作的实例端口
	RestoreInfos []BackupInfo `json:"restore_infos"  validate:"required"` // 需要待恢复备份文件组
}

// 运行是需要的必须参数,可以提前计算
type RestoreRunTimeCtx struct {
	LocalDB *sqlserver.DbWorker
}

// Init 初始化
func (r *RestoreDBSComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
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
	r.LocalDB = LWork
	// 校验所有待恢复的文件是否存在

	return nil
}

// PreCheck 预检测
func (r *RestoreDBSComp) PreCheck() error {
	isError := false
	if len(r.Params.RestoreInfos) == 0 {
		return fmt.Errorf("the file group to be restored is empty, check")
	}
	// 遍历每个文件的本地存在性
	for _, info := range r.Params.RestoreInfos {
		for _, file := range info.BakFiles {
			f := osutil.WINSFile{FileName: file}
			err, check := f.FileExists()
			if err != nil {
				return err
			}
			// 如果文件不存在，则存入error列表，聚合输出
			if !check {
				logger.Error(" database [%s] badkup dir [%s] not exists", info.DBName, file)
				isError = true
			}
		}
	}
	if isError {
		return fmt.Errorf("PerCheck is failed")
	}
	return nil
}

// CheckRestoreReasonableness 检测恢复备份文件组合法性
// 合法性包括：
// 1：恢复后磁盘容量是否满足
// 2: 是否是链式备份文件组
// 3: 备份文件是否可以支持恢复
func (r *RestoreDBSComp) CheckRestoreReasonableness(bakFiles []string) error {
	return nil
}
