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

// ClusterRoleSwitchComp 卸载SQLServer
type ClusterRoleSwitchComp struct {
	GeneralParam *components.GeneralParam
	Params       *ClusterRoleSwitchParam
	switchRunTimeCtx
}

// ClusterRoleSwitchParam 参数
type ClusterRoleSwitchParam struct {
	Host       string `json:"host" validate:"required,ip" `          // 本地hostip，指的是新主ip
	Port       int    `json:"port"  validate:"required,gt=0"`        // 需要操作的实例端口,指的是新主端口
	MasterHost string `json:"master_host" validate:"required,ip" `   // 当前master的ip
	MasterPort int    `json:"master_port"  validate:"required,gt=0"` // 当前master的port
	Force      bool   `json:"force"`                                 // 是否强制切换
	SyncMode   int    `json:"sync_mode" validate:"required"`         // 同步模式
}

// 运行是需要的必须参数,可以提前计算
type switchRunTimeCtx struct {
	MasterDB    *sqlserver.DbWorker
	NewMasterDB *sqlserver.DbWorker
	isEmpty     bool
}

// execResult todo
type execResult struct {
	Msg      string `db:"msg"`
	ExitCode int    `db:"exitcode"`
}

// Init 初始化
func (c *ClusterRoleSwitchComp) Init() error {
	var MdbWork *sqlserver.DbWorker
	var SdbWork *sqlserver.DbWorker
	var err error
	if MdbWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.MasterHost,
		c.Params.MasterPort,
	); err != nil {
		// 如果主实例连接失败，且不属于强制切换，则退出异常
		if c.Params.Force {
			return fmt.Errorf("connenct by [%s:%d] failed,err:%s",
				c.Params.MasterHost, c.Params.MasterPort, err.Error())
		}
		logger.Warn("connenct by [%s:%d] failed,err:%s",
			c.Params.MasterHost, c.Params.MasterPort, err.Error())
		return err
	}
	if SdbWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.Host,
		c.Params.Port,
	); err != nil {
		// 如果从实例连接失败，则退出异常(无论是不是强制切换)
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	c.MasterDB = MdbWork
	c.NewMasterDB = SdbWork

	return nil

}

// PreCheck 预检查
// 必须检查事项：同步情况检查，包括断开，延迟 有异常不能切换
func (c *ClusterRoleSwitchComp) PreCheck() error {
	// 检查模式是否支持
	if c.Params.SyncMode != cst.MIRRORING && c.Params.SyncMode != cst.ALWAYSON {
		return fmt.Errorf("the sync-mode [%d] is not supported", c.Params.SyncMode)
	}
	// 检查是否空实例（没有业务数据库）
	var checkDBS []string
	if err := c.MasterDB.Queryx(&checkDBS, cst.GET_BUSINESS_DATABASE); err != nil {
		return fmt.Errorf("get db list failed %v", err)
	}
	if len(checkDBS) == 0 {
		// 空时候代表不需要进行下面逻辑，打tag
		c.isEmpty = true
		logger.Warn("this cluster is an empty cluster")
		return nil
	}
	// 检验逻辑,不同数据同步模式检测方式不一样，分开处理, 强制切换不做检测处理
	if c.Params.Force {
		switch c.Params.SyncMode {
		case cst.MIRRORING:
			c.MirroringPreCheck()
		case cst.ALWAYSON:
			c.AlwaysOnPreCheck()
		default:
			return fmt.Errorf(
				"this synchronization mode switch [%d] is not supported for the time being", c.Params.SyncMode,
			)
		}
	}

	return nil
}

// MirroringPreCheck 对mirroring同步场景做相关检测
func (c *ClusterRoleSwitchComp) MirroringPreCheck() error {
	var adnormalDBS []string
	// 检测镜像库的异常情况
	if err := c.MasterDB.Queryx(&adnormalDBS, cst.CHECK_MIRRORING_ABNORMAL); err != nil {
		return fmt.Errorf("check-mirroring-abnormal failed %v", err)
	}
	if len(adnormalDBS) != 0 {
		return fmt.Errorf("detect databases with mirroring synchronization exceptions: %v", adnormalDBS)
	}
	// 检测延时落后大于1GB的镜像库
	if err := c.MasterDB.Queryx(&adnormalDBS, cst.CHECK_MIRRORING_DB_DELAY); err != nil {
		return fmt.Errorf("check-mirroring-delay-1GB failed %v", err)
	}
	if len(adnormalDBS) != 0 {
		return fmt.Errorf("detect mirroring-databases with latency greater than 1GB: %v", adnormalDBS)
	}
	return nil
}

// AlwaysOnPreCheck 对alwayson同步场景做相关检测
func (c *ClusterRoleSwitchComp) AlwaysOnPreCheck() error {
	var adnormalDBS []string
	var checkCnt int
	// ALWAYSON是否有没有副本机器
	if err := c.MasterDB.Queryxs(&checkCnt, cst.CHECK_ALWAYSON_NO_COPY); err != nil {
		return fmt.Errorf("check-alwayson-no-copy failed %v", err)
	}
	if checkCnt == 0 {
		return fmt.Errorf("detect ALWAYSON no copy")
	}
	// ALWAYSON 数据同步是否异常
	if err := c.MasterDB.Queryxs(&checkCnt, cst.CHECK_ALWAYSON_ABNORMAL); err != nil {
		return fmt.Errorf("check-alwayson-dbnormal failed %v", err)
	}
	if checkCnt != 0 {
		return fmt.Errorf("alwayson replicates abnormal nodes: %d", checkCnt)
	}
	// 查看ALWAYSON情况下，数据库同步异常的情况
	if err := c.MasterDB.Queryx(&adnormalDBS, cst.CHECK_ALWAYSON_DB_ABNORMAL); err != nil {
		return fmt.Errorf("check-alwayson-db-dbnormal  failed %v", err)
	}
	if len(adnormalDBS) != 0 {
		return fmt.Errorf("alwayson db with replication exception %v", adnormalDBS)
	}
	// 查看ALWAYSON情况下，数据库没有配置同步的情况
	if err := c.MasterDB.Queryx(&adnormalDBS, cst.CHECK_ALWAYSON_DB_NO_DEPLOY); err != nil {
		return fmt.Errorf("check-alwayson-db-no-deploy  failed %v", err)
	}
	if len(adnormalDBS) != 0 {
		return fmt.Errorf("alwayson db with no-deploy %v", adnormalDBS)
	}
	// 查看ALWAYSON延时落后大于1GB的情况
	if err := c.MasterDB.Queryx(&adnormalDBS, cst.CHECK_ALWAYSON_DB_DELAY); err != nil {
		return fmt.Errorf("check-alwayson-db-delay  failed %v", err)
	}
	if len(adnormalDBS) != 0 {
		return fmt.Errorf("alwayson db with delay-1GB %v", adnormalDBS)
	}

	return nil
}

// ExecSwitch TODO
// ExecSwitch 执行切换逻辑
func (c *ClusterRoleSwitchComp) ExecSwitch() (err error) {
	// 根据不同场景做切换sp
	if c.Params.Force {
		// 强制切换（主故障切换）
		if err := execSwitchSP(c.NewMasterDB, "Sys_AutoSwitch_DrToDb"); err != nil {
			return err
		}

	} else {
		// 主从互切
		switch c.Params.SyncMode {
		case cst.MIRRORING:
			if err := execSwitchSP(c.MasterDB, "Sys_AutoSwitch_FailOver"); err != nil {
				// 执行回滚操作
				execSwitchSP(c.NewMasterDB, "Sys_AutoSwitch_FailOver")
				return err
			}

			if err := execSwitchSP(c.NewMasterDB, "Sys_AutoSwitch_SafetyOff"); err != nil {
				return err
			}

			if err := execSwitchSP(c.NewMasterDB, "Sys_AutoSwitch_Resume"); err != nil {
				return err
			}

		case cst.ALWAYSON:
			if err := execSwitchSP(c.NewMasterDB, "Sys_AutoSwitch_FailOver"); err != nil {
				// 执行回滚操作
				execSwitchSP(c.MasterDB, "Sys_AutoSwitch_FailOver")
				return err
			}
			if err := execSwitchSP(c.NewMasterDB, "Sys_AutoSwitch_Resume"); err != nil {
				return err
			}

		default:
			return fmt.Errorf(
				"this synchronization mode switch [%d] is not supported for the time being", c.Params.SyncMode,
			)
		}

	}
	return nil
}

// exec_switch_sp todo
func execSwitchSP(db *sqlserver.DbWorker, spName string) error {
	cmd := fmt.Sprintf(cst.EXEC_SWITCH_SP_TMEP_SQL, spName)
	logger.Info(cmd)
	var ret []execResult
	if err := db.Queryx(&ret, cmd); err != nil {
		logger.Error("exec %s failed", spName)
		return err
	}
	if ret[0].ExitCode != 1 {
		logger.Error("exec %s failed", spName)
		return fmt.Errorf(ret[0].Msg)
	}
	logger.Info(ret[0].Msg)
	return nil
}
