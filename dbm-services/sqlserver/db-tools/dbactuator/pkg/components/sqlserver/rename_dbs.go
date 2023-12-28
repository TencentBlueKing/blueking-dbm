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
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// RenameDBSComp 克隆用户权限
type RenameDBSComp struct {
	GeneralParam *components.GeneralParam
	Params       *RenameDBSParam
	renameDBSrunTimeCtx
}

// RenameDBSParam 参数
type RenameDBSParam struct {
	Host      string         `json:"host" validate:"required,ip" `    // 本地hostip
	Port      int            `json:"port"  validate:"required,gt=0"`  // 需要操作的实例端口
	RenameDBS []RenameInfo   `json:"rename_dbs" validate:"required" ` // 待重命名库的列表
	Slaves    []cst.Instnace `json:"slaves" `                         // 集群的从实例
	SyncMode  int            `json:"sync_mode" validate:"required"`   // 集群的同步模式分别是：single:3/mirroring:2/alwayson:1
}

type RenameInfo struct {
	DBName       string `json:"db_name" validate:"required" `
	TargetDBName string `json:"target_db_name" validate:"required" `
}

// runTimeCtx 上下文
type renameDBSrunTimeCtx struct {
	DB      *sqlserver.DbWorker
	DRS     []slaves
	RealDBS []RenameInfo
}

// slaves todo
type slaves struct {
	Host   string
	Port   int
	Connet *sqlserver.DbWorker
}

// Init初始化
func (r *RenameDBSComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
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
	// 从实例初始化连接
	for _, s := range r.Params.Slaves {
		var SWork *sqlserver.DbWorker
		if SWork, err = sqlserver.NewDbWorker(
			r.GeneralParam.RuntimeAccountParam.SAUser,
			r.GeneralParam.RuntimeAccountParam.SAPwd,
			s.Host,
			s.Port,
		); err != nil {
			logger.Error("connenct by [%s:%d] failed,err:%s",
				r.Params.Host, r.Params.Port, err.Error())
			return err
		}
		r.DRS = append(r.DRS, slaves{
			Host:   s.Host,
			Port:   s.Port,
			Connet: SWork,
		})
	}
	return nil
}

// PerCheck 预检测
func (r *RenameDBSComp) PerCheck() error {
	var isErr bool
	for _, i := range r.Params.RenameDBS {
		// 判断DB是否有相关请求
		if !r.DB.CheckDBProcessExist(i.DBName) {
			logger.Error("[%s] db-process exist,check", i.DBName)
			isErr = true
		}
		var sql string = "select count(0) as cnt from master.sys.databases where name = '%s';"
		var cnt int
		// 判断源库名是否存在，如果不存在，打印日志，但不作为报错
		checkOldDBSQL := fmt.Sprintf(sql, i.DBName)
		if err := r.DB.Queryxs(&cnt, checkOldDBSQL); err != nil {
			logger.Error("check-db failed:%v", err)
			isErr = true
		}
		if cnt == 0 {
			// 代表DB不存在
			logger.Warn("[%s] DB not exists,skip", i.DBName)
			continue
		}
		// 判断目标库名是否存在，如果存在，打印日志，并且作为异常
		checkTargetDBSQL := fmt.Sprintf(sql, i.TargetDBName)
		if err := r.DB.Queryxs(&cnt, checkTargetDBSQL); err != nil {
			logger.Error("check-target-db failed:%v", err)
			isErr = true
		}
		if cnt != 0 {
			// 代表目标DB已存在，报错
			logger.Error("[%s] target-db already exists,check", i.TargetDBName)
			isErr = true
			continue
		}
		// 没有报错则加入待重命名数组
		r.RealDBS = append(r.RealDBS, i)
	}
	if isErr {
		return fmt.Errorf("precheck error")
	}
	if len(r.RealDBS) == 0 {
		return fmt.Errorf("no need to rename the databases , check")
	}
	return nil
}

// DoRenameDB 执行数据库重命名
func (r *RenameDBSComp) DoRenameDBS() error {
	var err error
	switch r.Params.SyncMode {
	case cst.SINGLE:
		err = r.DoRenameDBWithMirroring()
	case cst.MIRRORING:
		err = r.DoRenameDBWithMirroring()
	case cst.ALWAYSON:
		err = r.DoRenameDBWithAlwayson()
	default:
		return fmt.Errorf("this sync-mode [%d] of operation is not supported", r.Params.SyncMode)
	}
	if err != nil {
		return err
	}
	return nil
}

// DoRenameDBWithMirroring 在mirroring场景下，执行数据库重命名
func (r *RenameDBSComp) DoRenameDBWithMirroring() error {
	var isErr bool
	for _, i := range r.RealDBS {
		var cnt int
		var execDBSQLs []string
		checkSQL := fmt.Sprintf(
			`select count(0) as cnt from master.sys.database_mirroring where 
			 database_id= DB_ID('%s') and mirroring_guid is not null`,
			i.DBName,
		)
		if err := r.DB.Queryxs(&cnt, checkSQL); err != nil {
			logger.Error("check-db failed %v", err)
			isErr = true
		}
		// 表示有建立镜像关系，所以rename之前需要解除
		if cnt != 0 {
			execDBSQLs = append(execDBSQLs, fmt.Sprintf("ALTER DATABASE %s SET PARTNER OFF;", i.DBName))
		}
		execDBSQLs = append(execDBSQLs, fmt.Sprintf("ALTER DATABASE %s MODIFY NAME = %s", i.DBName, i.TargetDBName))
		// 执行rename 命令
		if _, err := r.DB.ExecMore(execDBSQLs); err != nil {
			logger.Error(
				"exec rename database [%s->%s] in DB [%s:%s] failed: [%v]",
				i.DBName,
				i.TargetDBName,
				r.Params.Host,
				r.Params.Port,
				err,
			)
			isErr = true
		}
	}
	if isErr {
		return fmt.Errorf("rename databases error")
	}
	return nil
}

// DoRenameDBWithAlwayson 在alwayson场景下，执行数据库重命名
func (r *RenameDBSComp) DoRenameDBWithAlwayson() error {
	var isErr bool
	for _, i := range r.RealDBS {
		var cnt int
		var execDBSQLs []string
		checkSQL := fmt.Sprintf(
			`select count(0) as cnt from master.sys.databases where 
			"name= '%s' and replica_id is not null`,
			i.DBName,
		)
		if err := r.DB.Queryxs(&cnt, checkSQL); err != nil {
			logger.Error("check-db failed %v", err)
			isErr = true
		}
		// 表示有建立镜像关系，所以rename之前需要解除可用组
		if cnt != 0 {
			var groupName string
			var err error
			if groupName, err = r.DB.GetGroupName(); err != nil {
				logger.Error("get groupname failed:%v", err)
				isErr = true
			}
			execDBSQLs = append(
				execDBSQLs,
				fmt.Sprintf("ALTER AVAILABILITY GROUP %s REMOVE DATABASE %s;", groupName, i.DBName),
			)
		}
		execDBSQLs = append(
			execDBSQLs,
			fmt.Sprintf("ALTER DATABASE %s MODIFY NAME = %s;", i.DBName, i.TargetDBName),
		)
		// 执行rename 命令
		if _, err := r.DB.ExecMore(execDBSQLs); err != nil {
			logger.Error(
				"exec rename database [%s->%s] in DB [%s:%s] failed: [%v]",
				i.DBName,
				i.TargetDBName,
				r.Params.Host,
				r.Params.Port,
				err,
			)
			isErr = true
		}
	}
	if isErr {
		return fmt.Errorf("rename databases error")
	}
	return nil

}
