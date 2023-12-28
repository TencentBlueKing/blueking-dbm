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
	"fmt"
	"strings"

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
	MirroringState       int    `db:"mirroring_state"`
	MirroringPartnerName string `db:"mirroring_partner_name"`
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
		c.Params.Host,
		c.Params.Port,
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
			"select count(0) from master.sys.databases where is_read_only == 0 or state == 0 and name = '%s' ;",
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
	sqlStr := fmt.Sprintf(cst.GET_CREATE_END_POINT_SQL, c.ListenPort, "%s")

	// 在DB执行create sql
	if _, err := c.DB.Exec(sqlStr); err != nil {
		logger.Error("exec create endpoint in DB [%s:%s] failed", c.Params.Host, c.Params.Port)
		return err
	}

	// 在DR执行create sql
	if _, err := c.DR.Exec(sqlStr); err != nil {
		logger.Error("exec create endpoint in DR [%s:%s] failed", c.Params.DRHost, c.Params.DRPort)
		return err
	}

	return nil
}

// CreateDBMirroring DB维度建立镜像库
func (c *CreateMirrorComp) CreateDBMirroring() error {
	var isErr bool
	for _, dbName := range c.ReadDBS {
		var info []DataBaseMirroring
		checkSQL := fmt.Sprintf(
			"select mirroring_state,mirroring_partner_name from master.sys.database_mirroring where database_id = DB_ID('%s')",
			dbName,
		)
		if err := c.DB.Queryx(&info, checkSQL); err != nil {
			logger.Error("check db mirroring %s failed: %v", dbName, err)
			isErr = true
		}
		if strings.Contains(info[0].MirroringPartnerName, fmt.Sprintf("%s:%d", c.Params.DRHost, c.ListenPort)) &&
			(info[0].MirroringState != 0 && info[0].MirroringState != 1) {
			// 认为这类DB建立好镜像库，不需要重新建立
			continue
		}
		dbExecSQLs := []string{
			fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER OFF", dbName),
			fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER = 'TCP://%s:%d'", dbName, c.Params.DRHost, c.ListenPort),
			fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER SAFETY OFF", dbName),
		}
		drExecSQLs := []string{
			fmt.Sprintf("ALTER DATABASE [%s] SET PARTNER = 'TCP://%s:%d'", dbName, c.Params.Host, c.ListenPort),
		}
		// 在dr执行
		if _, err := c.DR.ExecMore(drExecSQLs); err != nil {
			logger.Error("exec SET PARTNER in DR [%s:%s] failed", c.Params.DRHost, c.Params.DRPort)
			isErr = true
		}
		// 在db执行
		if _, err := c.DB.ExecMore(dbExecSQLs); err != nil {
			logger.Error("exec SET PARTNER in DB [%s:%s] failed", c.Params.Host, c.Params.Port)
			return err
		}

	}
	if isErr {
		return fmt.Errorf("create dbs mirroring error")
	}

	return nil
}
