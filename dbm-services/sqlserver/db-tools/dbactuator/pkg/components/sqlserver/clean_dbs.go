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
	"reflect"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CleanDBSComp 克隆用户权限
type CleanDBSComp struct {
	GeneralParam *components.GeneralParam
	Params       *CleanDBSParam
	cleanDBSrunTimeCtx
}

// CleanDBSParam 参数
type CleanDBSParam struct {
	Host              string         `json:"host" validate:"required,ip" `            // 本地hostip
	Port              int            `json:"port"  validate:"required,gt=0"`          // 需要操作的实例端口
	CleanDBS          []string       `json:"clean_dbs" validate:"required" `          // 待清理库的列表
	SyncMode          int            `json:"sync_mode" validate:"required"`           // 集群的同步模式分别是：single:3/mirroring:2/alwayson:1
	CleanMode         string         `json:"clean_mode" validate:"required"`          //这次的清档类型：clean_tables/drop_tables/drop_dbs
	Slaves            []cst.Instnace `json:"slaves" `                                 // 集群的从实例
	CleanTables       []string       `json:"clean_tables" validate:"required"`        // 清理表信息
	IgnoreCleanTables []string       `json:"ignore_clean_tables" validate:"required"` // 忽略清理表信息

}

// runTimeCtx 上下文
type cleanDBSrunTimeCtx struct {
	DB      *sqlserver.DbWorker
	DRS     []slaves
	RealDBS []string
}

// Init初始化
func (c *CleanDBSComp) Init() error {
	var LWork *sqlserver.DbWorker
	var err error
	// 初始化本地实例连接
	if LWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.Host,
		c.Params.Port,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	c.DB = LWork
	// 从实例初始化连接
	for _, s := range c.Params.Slaves {
		var SWork *sqlserver.DbWorker
		if SWork, err = sqlserver.NewDbWorker(
			c.GeneralParam.RuntimeAccountParam.SAUser,
			c.GeneralParam.RuntimeAccountParam.SAPwd,
			s.Host,
			s.Port,
		); err != nil {
			logger.Error("connenct by [%s:%d] failed,err:%s",
				c.Params.Host, c.Params.Port, err.Error())
			return err
		}
		c.DRS = append(c.DRS, slaves{
			Host:   s.Host,
			Port:   s.Port,
			Connet: SWork,
		})
	}
	return nil
}

// PerCheck 预检测
func (c *CleanDBSComp) PerCheck() error {
	var isErr bool
	for _, dbName := range c.Params.CleanDBS {
		// 判断DB是否有相关请求
		if !c.DB.CheckDBProcessExist(dbName) {
			logger.Error("[%s] db-process exist,check", dbName)
			isErr = true
		}
		var sql string = "select count(0) as cnt from master.sys.databases where name = '%s';"
		var cnt int
		// 判断源库名是否存在，如果不存在，打印日志，但不作为报错
		checkOldDBSQL := fmt.Sprintf(sql, dbName)
		if err := c.DB.Queryxs(&cnt, checkOldDBSQL); err != nil {
			logger.Error("check-db failed:%v", err)
			isErr = true
		}
		if cnt == 0 {
			// 代表DB不存在
			logger.Warn("[%s] DB not exists,skip", dbName)
			continue
		}
		// 没有报错则加入待重命名数组
		c.RealDBS = append(c.RealDBS, dbName)
	}
	if isErr {
		return fmt.Errorf("precheck error")
	}
	if len(c.RealDBS) == 0 {
		logger.Warn("no need to clean the databases , check")
		return nil
	}
	return nil
}

// DoCleanDBS 执行清档逻辑
func (c *CleanDBSComp) DoCleanDBS() error {

	if len(c.RealDBS) == 0 {
		// 没有库可操作，正常退出
		return nil
	}

	switch c.Params.CleanMode {
	case "clean_tables":
		if err := c.CleanTablesInDBS(); err != nil {
			return err
		}
	case "drop_tables":
		if err := c.DropTablesInDBS(); err != nil {
			return err
		}
	case "drop_dbs":
		if err := c.DropDBS(); err != nil {
			return err
		}
	default:
		return fmt.Errorf("this clean-mode [%s] of operation is not supported", c.Params.CleanMode)
	}
	return nil
}

// CleanTablesInDBS 清空数据，保留表结构
func (c *CleanDBSComp) CleanTablesInDBS() error {
	var isErr bool
	for _, dbName := range c.RealDBS {

		if reflect.DeepEqual(c.Params.CleanTables, []string{"*"}) && len(c.Params.IgnoreCleanTables) == 0 {
			// 如果是全匹配，直接使用 sp_MSForEachTable 处理
			execSQL := fmt.Sprintf(cst.TRUNCATE_TABLES_SQL, dbName)
			if _, err := c.DB.Exec(execSQL); err != nil {
				logger.Error(
					"exec clean tables in database [%s] failed: [%v], execSQL: [%v]",
					dbName,
					err,
					execSQL,
				)
				isErr = true
			}
		} else {
			// 非匹配模式处理
			if err := c.execTablesForPer("truncate", dbName); err != nil {
				return err
			}
		}

	}
	if isErr {
		return fmt.Errorf("clean tables error")
	}
	return nil
}

// DropTablesInDBS 清空数据，并且表结构
func (c *CleanDBSComp) DropTablesInDBS() error {
	var isErr bool
	for _, dbName := range c.RealDBS {
		if reflect.DeepEqual(c.Params.CleanTables, []string{"*"}) && len(c.Params.IgnoreCleanTables) == 0 {
			execSQL := fmt.Sprintf(cst.DROP_TABLES_SQL, dbName)
			// 执行命令
			if _, err := c.DB.Exec(execSQL); err != nil {
				logger.Error(
					"exec drop tables in database [%s] failed: [%v]",
					dbName,
					err,
				)
				isErr = true
			}
		} else {
			// 非匹配模式处理
			if err := c.execTablesForPer("drop", dbName); err != nil {
				return err
			}
		}

	}
	if isErr {
		return fmt.Errorf("drop tables error")
	}
	return nil
}

// DropDBS 删除库
func (c *CleanDBSComp) DropDBS() error {
	var isErr bool
	for _, dbName := range c.RealDBS {
		switch c.Params.SyncMode {
		case cst.ALWAYSON:
			if err := c.DropdbwithAlwayson(dbName); err != nil {
				logger.Error(err.Error())
				isErr = true
			}
		case cst.MIRRORING:
			if err := c.DropdbwithMirroring(dbName); err != nil {
				logger.Error(err.Error())
				isErr = true
			}
		default:
			if err := c.DropdbwithMirroring(dbName); err != nil {
				logger.Error(err.Error())
				isErr = true
			}
		}
	}
	if isErr {
		return fmt.Errorf("drop databases error")
	}
	return nil
}

func (c *CleanDBSComp) DropdbwithMirroring(dbName string) error {
	var cnt int
	var checkSQL string
	var dbSnapshots []string
	var execDBSQLs []string

	// mirroring  判断同步方法
	checkSQL = fmt.Sprintf(
		`select count(0) as cnt from master.sys.database_mirroring where 
			database_id= DB_ID('%s') and mirroring_guid is not null`,
		dbName,
	)

	if err := c.DB.Queryxs(&cnt, checkSQL); err != nil {
		return fmt.Errorf("check-db failed %v", err)
	}
	// 表示有建立镜像关系，所以drop之前需要解除
	if cnt != 0 {
		execDBSQLs = append(execDBSQLs, fmt.Sprintf("ALTER DATABASE %s SET PARTNER OFF;", dbName))
	}
	// 查询数据库是否有关联的快照库
	getSnapshots := fmt.Sprintf(
		"select name from master.sys.databases where source_database_id = DB_ID('%s')",
		dbName,
	)
	if err := c.DB.Queryx(&dbSnapshots, getSnapshots); err != nil {
		return fmt.Errorf("get-db-snapshots failed %v", err)
	}

	// 如果有存在快照，则先删除快照库
	if len(dbSnapshots) != 0 {
		for _, snapshot := range dbSnapshots {
			execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE %s;", snapshot))
		}
	}
	// 拼接执行删除源库
	execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE %s", dbName))

	// 执行drop 批命令
	if _, err := c.DB.ExecMore(execDBSQLs); err != nil {
		return fmt.Errorf(
			"exec drop database [%s] in DB [%s:%d] failed: [%v]",
			dbName,
			c.Params.Host,
			c.Params.Port,
			err,
		)
	}
	// 从实例删除从库
	if err := DropOldDatabaseOnslave(dbName, c.DRS); err != nil {
		return err
	}
	return nil
}

// DropdbwithAlwayson 在Alwayson场景删除库
func (c *CleanDBSComp) DropdbwithAlwayson(dbName string) error {
	var cnt int
	var checkSQL string
	var dbSnapshots []string
	var execDBSQLs []string
	checkSQL = fmt.Sprintf(
		`select count(0) as cnt from master.sys.databases where 
		name= '%s' and replica_id is not null`,
		dbName,
	)
	if err := c.DB.Queryxs(&cnt, checkSQL); err != nil {
		return fmt.Errorf("check-db failed %v", err)
	}
	// 表示有建立同步关系，所以drop之前需要解除
	if cnt != 0 {
		var groupName string
		var err error
		if groupName, err = c.DB.GetGroupName(); err != nil {
			return fmt.Errorf("get groupname failed:%v", err)
		}
		execDBSQLs = append(
			execDBSQLs,
			fmt.Sprintf("ALTER AVAILABILITY GROUP %s REMOVE DATABASE %s;", groupName, dbName),
		)
	}
	// 查询数据库是否有关联的快照库
	getSnapshots := fmt.Sprintf(
		"select name from master.sys.databases where source_database_id = DB_ID('%s')",
		dbName,
	)
	if err := c.DB.Queryx(&dbSnapshots, getSnapshots); err != nil {
		return fmt.Errorf("get-db-snapshots failed %v", err)
	}

	// 如果有存在快照，则先删除快照库
	if len(dbSnapshots) != 0 {
		for _, snapshot := range dbSnapshots {
			execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE %s;", snapshot))
		}
	}
	// 拼接执行删除源库
	execDBSQLs = append(execDBSQLs, fmt.Sprintf("DROP DATABASE %s", dbName))

	// 执行drop 批命令
	if _, err := c.DB.ExecMore(execDBSQLs); err != nil {
		return fmt.Errorf(
			"exec drop database [%s] in DB [%s:%d] failed: [%v]",
			dbName,
			c.Params.Host,
			c.Params.Port,
			err,
		)
	}

	// 从实例删除从库
	if err := DropOldDatabaseOnslave(dbName, c.DRS); err != nil {
		return err
	}

	return nil
}

// execTablesForPer 非全匹配规则，每个表变量操作
func (c *CleanDBSComp) execTablesForPer(execMode string, dbName string) error {
	var execSQLs []string
	var realTables []string
	var err error
	if realTables, err = c.DB.GetTableListOnDB(
		dbName,
		c.Params.CleanTables,
		c.Params.IgnoreCleanTables); err != nil {
		return fmt.Errorf("get tables list on db [%s] failed:[%v]", dbName, err)

	}
	if len(realTables) == 0 {
		// 获取的表列表为空，正常跳过
		logger.Info(
			"table-list is empty on db [%s], skip. CleanTables:[%v];IgnoreCleanTables[%v]",
			dbName,
			c.Params.CleanTables,
			c.Params.IgnoreCleanTables,
		)
		return nil
	}
	for _, t := range realTables {
		switch execMode {
		case "truncate":
			execSQLs = append(execSQLs, fmt.Sprintf(
				cst.TRUNCATE_TABLES_SQL_FOR_PER,
				dbName, t, t, t, t, t,
			))
		case "drop":
			execSQLs = append(execSQLs, fmt.Sprintf(
				cst.DROP_TABLES_SQL_FOR_PER,
				dbName, t, t, t,
			))
		default:
			return fmt.Errorf("execMode [%s] not suppurt", execMode)
		}

	}
	if _, err := c.DB.ExecMore(execSQLs); err != nil {
		return fmt.Errorf(
			"exec clean tables in database [%s] failed: [%v]; execSQls:[%v]",
			dbName,
			err,
			execSQLs,
		)
	}
	logger.Info("exec [%s] successfully on db [%s]", execMode, dbName)
	return nil
}
