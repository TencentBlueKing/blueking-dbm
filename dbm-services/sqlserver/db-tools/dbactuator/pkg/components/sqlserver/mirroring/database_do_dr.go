/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mirroring

import (
	"database/sql"
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CreateMirrorComp 配置
type CreateMirrorComp struct {
	GeneralParam *components.GeneralParam
	Params       *CreateMirrorParam
	CreateRunTimeCtx
}

// CreateMirrorParam 参数
type CreateMirrorParam struct {
	Host   string   `json:"host" validate:"required,ip" `      // 本地hostip
	Port   int      `json:"port"  validate:"required,gt=0"`    // 需要操作的实例端口
	DRHost string   `json:"dr_host" validate:"required,ip" `   // 做dr的hostip
	DRPort int      `json:"dr_port"  validate:"required,gt=0"` // 做dr需要操作的实例端口
	DBS    []string `json:"dbs"  validate:"required"`          // 做镜像的数据库列表
}

// CreateRunTimeCtx 上下文
type CreateRunTimeCtx struct {
	DB         *sqlserver.DbWorker
	DR         *sqlserver.DbWorker
	ReadDBS    []string
	ListenPort int
}

// DataBaseMirroring todo
type DataBaseMirroring struct {
	MirroringState       sql.NullInt16  `db:"mirroring_state"`
	MirroringPartnerName sql.NullString `db:"mirroring_partner_name"`
}

// Init 初始化
func (c *CreateMirrorComp) Init() error {
	var LWork *sqlserver.DbWorker
	var DRWork *sqlserver.DbWorker
	var err error
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
	if DRWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.DRHost,
		c.Params.DRPort,
	); err != nil {
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	c.DB = LWork
	c.DR = DRWork
	// 根据实例端口计算出endpoint 监听端口
	c.ListenPort = osutil.GetListenPort(c.Params.Port)

	return nil
}

// PreCheck 预检测
func (c *CreateMirrorComp) PreCheck() error {
	// 检测每个DB是否存在
	for _, dbName := range c.Params.DBS {
		var cnt int
		checkCmd := fmt.Sprintf(
			"select count(0) from master.sys.databases where is_read_only = 0 or state = 0 and name = '%s' ;",
			dbName,
		)
		if err := c.DB.Queryxs(&cnt, checkCmd); err != nil {
			return fmt.Errorf("check-db failed %v", err)
		}
		if cnt != 0 {
			c.ReadDBS = append(c.ReadDBS, dbName)
		} else {
			// 检测到数据库不存在或者状态异常
			logger.Warn("[%s] db no longer exists or is abnormal ", dbName)
		}
	}
	return nil
}

// CreateEndPoint 建立对端关系
func (c *CreateMirrorComp) CreateEndPoint() error {
	sqlStr := []string{
		cst.GET_DROP_END_POINT_SQL,
		fmt.Sprintf(cst.GET_CREATE_END_POINT_SQL, c.ListenPort),
	}

	// 在DB执行create sql, 兼容2008版本使用ExecMoreNoSA方法
	if _, err := c.DB.ExecMoreNoSA(sqlStr); err != nil {
		logger.Error("exec create endpoint in DB [%s:%d] failed", c.Params.Host, c.Params.Port)
		return err
	}

	// 在DR执行create sql
	if _, err := c.DR.ExecMoreNoSA(sqlStr); err != nil {
		logger.Error("exec create endpoint in DR [%s:%d] failed", c.Params.DRHost, c.Params.DRPort)
		return err
	}

	return nil
}

// CreateDBMirroring DB维度建立镜像库
func (c *CreateMirrorComp) CreateDBMirroring() error {
	var isErr bool
	for _, dbName := range c.ReadDBS {
		var ret int
		checkSQL := fmt.Sprintf(
			"select count(0) as cnt from master.sys.database_mirroring where database_id = DB_ID('%s') and mirroring_guid is not null",
			dbName,
		)
		if err := c.DB.Queryxs(&ret, checkSQL); err != nil {
			logger.Error("check db mirroring %s failed: %v", dbName, err)
			isErr = true
		}
		if ret != 0 {
			// 认为这类DB之前有镜像配置，去掉
			offSQL := []string{
				fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER OFF", dbName),
			}
			if _, err := c.DB.ExecMore(offSQL); err != nil {
				logger.Error("exec [%s] SET PARTNER OFF in DB [%s:%d] failed", dbName, c.Params.DRHost, c.Params.DRPort)
				logger.Error("err: %v", err)
				isErr = true
				continue
			}
			logger.Info("exec [%s] SET PARTNER OFF in DB [%s:%d] successfully", dbName)
		}

		// 建立关系
		dbExecSQLs := []string{
			fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER = 'TCP://%s:%d'", dbName, c.Params.DRHost, c.ListenPort),
			fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER SAFETY OFF", dbName),
		}
		drExecSQLs := []string{
			fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER = 'TCP://%s:%d'", dbName, c.Params.Host, c.ListenPort),
		}

		// 在dr执行
		if _, err := c.DR.ExecMore(drExecSQLs); err != nil {
			logger.Error("exec [%s] SET PARTNER in DR [%s:%d] failed", dbName, c.Params.DRHost, c.Params.DRPort)
			logger.Error("err: %v", err)
			isErr = true
			continue
		}
		logger.Info("exec [%s]  SET PARTNER in DR [%s:%d] successfully", dbName, c.Params.DRHost, c.Params.DRPort)

		// 在db执行
		if _, err := c.DB.ExecMore(dbExecSQLs); err != nil {
			logger.Error("exec [%s] SET PARTNER in DB [%s:%d] failed", dbName, c.Params.Host, c.Params.Port)
			logger.Error("err: %v", err)
			isErr = true
			continue
		}
		logger.Info("exec [%s] SET PARTNER in DB [%s:%d] successfully", dbName, c.Params.Host, c.Params.Port)

	}
	if isErr {
		return fmt.Errorf("create dbs mirroring error")
	}

	return nil
}

// ExecSnapShot 切换后执行快照逻辑, 不异常退出
func (c *CreateMirrorComp) ExecSnapShot() (err error) {
	// 暂停10秒，足够时间同步数据
	time.Sleep(10 * time.Second)
	// 删除master的历史快照
	if err := sqlserver.ExecSwitchSP(c.DB, "Sys_AutoSwitch_SnapShot", "1,"); err != nil {
		logger.Error(fmt.Sprintf("exec Sys_AutoSwitch_SnapShot failed: %s", err.Error()))
	}
	// 创建slave的历史快照
	if err := sqlserver.ExecSwitchSP(c.DR, "Sys_AutoSwitch_SnapShot", "0,"); err != nil {
		logger.Error(fmt.Sprintf("exec Sys_AutoSwitch_SnapShot failed: %s", err.Error()))
	}
	return nil
}
