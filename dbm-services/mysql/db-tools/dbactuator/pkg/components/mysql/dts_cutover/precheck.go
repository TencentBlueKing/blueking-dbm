/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/dtsutil"
)

const precheckStatusTimeoutSec = 30

// PreCheck 切换前预检：源连通、表可展开且存在，再轮询到各源 Running 且 SBM==0。
// 本步骤不执行 FLUSH TABLES ... WITH READ LOCK，也不 stop、不探测权限。
// 多源按顺序 fail-fast。
func (c *Comp) PreCheck() error {
	if err := c.Init(); err != nil {
		return err
	}
	p := c.Params
	for _, ep := range p.SourceEndpoints {
		scope := ep.SyncScope
		if scope == nil || scope.IsEmpty() {
			scope = p.SyncScope
		}
		var useLockTables []dtsutil.TableItem
		if len(p.LockTables) > 0 {
			useLockTables = p.LockTables
		}
		if err := precheckOneSource(ep, scope, useLockTables); err != nil {
			return err
		}
	}

	if err := dtsutil.PollReadyBeforeLock(func() ([]dtsutil.TaskStatusItem, error) {
		resp, ferr := dtsutil.FetchTaskStatus(p.DtsMasterAddr, p.TaskName, precheckStatusTimeoutSec)
		if ferr != nil {
			return nil, ferr
		}
		return resp.Data, nil
	}, defaultPrecheckPollMax, func() { time.Sleep(precheckPollInterval) }); err != nil {
		return fmt.Errorf("预检追平失败（未加锁）: %w", err)
	}
	logger.Info("预检通过: sources=%d task=%s", len(p.SourceEndpoints), p.TaskName)
	return nil
}

func precheckOneSource(ep dtsutil.Endpoint, scope *dtsutil.SyncScope, lockTables []dtsutil.TableItem) error {
	srcLabel := fmt.Sprintf("%s:%d", ep.Host, ep.Port)
	if ep.SourceName != "" {
		srcLabel = fmt.Sprintf("%s(%s)", srcLabel, ep.SourceName)
	}
	inst := native.InsObject{
		Host: ep.Host,
		Port: ep.Port,
		User: ep.User,
		Pwd:  ep.Password,
	}
	worker, err := inst.Conn()
	if err != nil {
		return fmt.Errorf("预检连接源端 %s 失败: %w", srcLabel, err)
	}
	defer worker.Close()

	tables, err := dtsutil.ResolveTablesForPrecheck(worker.Db, scope, lockTables)
	if err != nil {
		return fmt.Errorf("预检源端 %s 表清单失败: %w", srcLabel, err)
	}
	logger.Info("预检源端 %s 表清单就绪 tables=%d", srcLabel, len(tables))
	return nil
}
