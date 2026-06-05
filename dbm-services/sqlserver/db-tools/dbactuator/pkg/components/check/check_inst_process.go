/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package check

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"
)

// CheckInstProcessComp 检查db连接情况
type CheckInstProcessComp struct {
	GeneralParam *components.GeneralParam
	Params       *CheckInstProcessParam
	DB           *sqlserver.DbWorker
}

// CheckInstProcessParam 参数
type CheckInstProcessParam struct {
	Host        string   `json:"host" validate:"required,ip" `   // 本地hostip
	Port        int      `json:"port"  validate:"required,gt=0"` // 需要操作的实例端口
	IsFroceKill bool     `json:"is_force_kill"`                  // 隐藏参数，是否强制回收业务进程
	DBList      []string `json:"db_list"`                        // 指定需要检查连接的db列表，不传则检查实例上所有业务库
}

// Init 初始化
func (c *CheckInstProcessComp) Init() error {
	var dbWork *sqlserver.DbWorker
	var err error
	if dbWork, err = sqlserver.NewDbWorker(
		c.GeneralParam.RuntimeAccountParam.SAUser,
		c.GeneralParam.RuntimeAccountParam.SAPwd,
		c.Params.Host,
		c.Params.Port,
	); err != nil {
		// 如果实例连接失败，则退出异常
		logger.Error("connenct by [%s:%d] failed,err:%s",
			c.Params.Host, c.Params.Port, err.Error())
		return err
	}
	c.DB = dbWork

	return nil

}

// CheckInstProcess 检查db连接情况
func (c *CheckInstProcessComp) CheckInstProcess() error {
	var procinfos []sqlserver.ProcessInfo
	checkSQL := cst.CHECK_INST_SQL
	if len(c.Params.DBList) > 0 {
		// 如果指定了db列表，则只检查这些db的连接情况
		quoted := make([]string, 0, len(c.Params.DBList))
		for _, db := range c.Params.DBList {
			// 单引号转义，避免SQL注入与语法异常
			quoted = append(quoted, fmt.Sprintf("'%s'", strings.ReplaceAll(db, "'", "''")))
		}
		dbFilter := fmt.Sprintf(" and DB_NAME(dbid) in (%s) ", strings.Join(quoted, ","))
		// 在 order by 之前插入过滤条件
		if idx := strings.Index(strings.ToLower(checkSQL), "order by"); idx >= 0 {
			checkSQL = checkSQL[:idx] + dbFilter + checkSQL[idx:]
		} else {
			checkSQL = checkSQL + dbFilter
		}
		logger.Info("check inst process with db_list: %v", c.Params.DBList)
	}
	if err := c.DB.Queryx(&procinfos, checkSQL); err != nil {
		return fmt.Errorf("check-inst-process failed %v", err)
	}
	if len(procinfos) == 0 {
		// 没有返回异常db列表则正常退出
		return nil
	}
	if c.Params.IsFroceKill {
		// 如果为true，则主动kill掉进程
		var killCmd []string
		for _, info := range procinfos {
			killCmd = append(killCmd, fmt.Sprintf("kill %d", info.Spid))
		}
		if _, err := c.DB.ExecMore(killCmd); err != nil {
			return fmt.Errorf("kill process failed %v", err)
		}
		logger.Info("killing inst-process successfully")
		return nil
	} else {
		// 如果IsFroceKill为false，异常退出输出；
		sqlserver.LogProcessInfos(
			"error",
			fmt.Sprintf("%s:%d active business connections", c.Params.Host, c.Params.Port),
			procinfos,
		)
		return fmt.Errorf(
			"[%s:%d] there is a business connections [%d], please check",
			c.Params.Host,
			c.Params.Port,
			len(procinfos),
		)
	}

}
