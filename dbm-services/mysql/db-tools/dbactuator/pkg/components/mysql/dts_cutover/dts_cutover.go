/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package dts_cutover 在 DTS Master 主机上执行 MySQL DTS 安全切换：
// 预检（源连通/表存在/子任务 Running，并在加锁前轮询到 SBM==0）→ 源端迁移表读锁 → 拍 master 位点快照并短时持锁复核 → Master HTTP API stop → 采位点 → 源端 unlock。
// 加锁前预检 1s×30。持锁复核 0.5s×60。持锁条件：SBM==0 且 syncer≥加锁瞬间 master 快照（不用实时 master≥syncer）。
// 持锁停止使用固定短超时（服务端 15s，HTTP 20s）。Stop 失败立即返回，由 defer unlock 释放源表读锁。
// 本期不对目标端加锁，不做域名/Proxy 切换。停任务与查状态统一走 Master OpenAPI。
// DTS 公共操作（OpenAPI 客户端/状态判定/位点/sync_scope/表锁）已抽取到 pkg/util/dtsutil。
package dts_cutover

import (
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/dtsutil"
)

const (
	defaultCatchupRecheck  = 3
	defaultPrecheckPollMax = 30
	precheckPollInterval   = 1 * time.Second
	defaultCatchupPollMax  = 60
	catchupPollInterval    = 500 * time.Millisecond
)

// Comp DTS cutover 组件。
type Comp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *Params                  `json:"extend"`
}

// Params Flow → actuator payload。
type Params struct {
	DtsMasterAddr   string              `json:"dts_master_addr" validate:"required"`
	DeployPath      string              `json:"deploy_path"` // 可选；停任务已改走 API，不再依赖本机 dmctl
	TaskName        string              `json:"task_name" validate:"required"`
	SourceEndpoints []dtsutil.Endpoint  `json:"source_endpoints" validate:"required,gt=0,dive"`
	SyncScope       *dtsutil.SyncScope  `json:"sync_scope"`
	LockTables      []dtsutil.TableItem `json:"lock_tables"`
	// CatchupRecheck：连续通过持锁快照追平的次数，默认 3
	CatchupRecheck int `json:"catchup_recheck"`
	// CatchupPollMax：持锁复核最大次数（含首次），默认 60；间隔 0.5s
	CatchupPollMax int `json:"catchup_poll_max"`
	// ApiTimeoutSec 保留给旧 payload。持锁停止不读它，固定走 StopTaskWhileLocked。
	ApiTimeoutSec   int `json:"api_timeout_sec"`
	DmctlTimeoutSec int `json:"dmctl_timeout_sec"` // deprecated: 同 ApiTimeoutSec
	// 编排透传。cutover 不读校验结果，也不据此改变追平。
	ChecksumPassed bool `json:"checksum_passed"`
	SkipChecksum   bool `json:"skip_checksum"`
}

// Example payload 示例（IP 使用 127.0.0.x）。
func (c *Comp) Example() interface{} {
	return Comp{
		Params: &Params{
			DtsMasterAddr: "127.0.0.2:18301",
			DeployPath:    "/data/dts/demo",
			TaskName:      "task-a",
			SourceEndpoints: []dtsutil.Endpoint{
				{
					Host:       "127.0.0.10",
					Port:       20000,
					User:       "u",
					Password:   "p",
					SourceName: "src1",
					SyncScope: &dtsutil.SyncScope{
						DoDBs:    []string{"app"},
						DoTables: []dtsutil.TableItem{{Schema: "*", Table: "*"}},
					},
				},
			},
			SyncScope: &dtsutil.SyncScope{
				DoDBs:    []string{"app"},
				DoTables: []dtsutil.TableItem{{Schema: "*", Table: "*"}},
			},
			CatchupRecheck: defaultCatchupRecheck,
			CatchupPollMax: defaultCatchupPollMax,
			ApiTimeoutSec:  600,
			ChecksumPassed: true,
			SkipChecksum:   false,
		},
	}
}

func (p *Params) stopTimeoutSec() int {
	if p.ApiTimeoutSec > 0 {
		return p.ApiTimeoutSec
	}
	if p.DmctlTimeoutSec > 0 {
		return p.DmctlTimeoutSec
	}
	return 600
}

func (p *Params) catchupPollMax() int {
	if p.CatchupPollMax > 0 {
		return p.CatchupPollMax
	}
	return defaultCatchupPollMax
}

// Init 参数校验与默认值。
func (c *Comp) Init() error {
	if c.Params == nil {
		return fmt.Errorf("params 为空")
	}
	p := c.Params
	if strings.TrimSpace(p.TaskName) == "" {
		return fmt.Errorf("task_name 为空")
	}
	if strings.TrimSpace(p.DtsMasterAddr) == "" {
		return fmt.Errorf("dts_master_addr 为空")
	}
	if len(p.SourceEndpoints) == 0 {
		return fmt.Errorf("source_endpoints 为空")
	}
	if len(p.LockTables) == 0 && (p.SyncScope == nil || p.SyncScope.IsEmpty()) {
		// 允许仅在各 endpoint 内嵌 sync_scope
		hasEPScope := false
		for _, ep := range p.SourceEndpoints {
			if ep.SyncScope != nil && !ep.SyncScope.IsEmpty() {
				hasEPScope = true
				break
			}
		}
		if !hasEPScope {
			return fmt.Errorf("sync_scope 与 lock_tables 均为空，拒绝执行（禁止无清单裸 FTWRL）")
		}
	}
	if p.CatchupRecheck <= 0 {
		p.CatchupRecheck = defaultCatchupRecheck
	}
	if p.CatchupPollMax <= 0 {
		p.CatchupPollMax = defaultCatchupPollMax
	}
	if p.CatchupPollMax < p.CatchupRecheck {
		p.CatchupPollMax = p.CatchupRecheck
	}
	p.ApiTimeoutSec = p.stopTimeoutSec()
	return nil
}

// Run 执行切换主路径（假定 Steps 已完成 Init/PreCheck；此处 Init 幂等兜底）。
func (c *Comp) Run() error {
	if err := c.Init(); err != nil {
		return err
	}
	p := c.Params
	logger.Info(
		"DTS cutover 开始 task=%s sources=%d recheck=%d poll_max=%d skip_checksum=%t",
		p.TaskName, len(p.SourceEndpoints), p.CatchupRecheck, p.CatchupPollMax, p.SkipChecksum,
	)

	for _, ep := range p.SourceEndpoints {
		logger.Info("锁定 %s:%d，DTS 也从这台读 binlog source_name=%s", ep.Host, ep.Port, ep.SourceName)
	}

	locks := make([]*dtsutil.SourceLockConn, 0, len(p.SourceEndpoints))
	defer func() {
		for i := len(locks) - 1; i >= 0; i-- {
			if uerr := dtsutil.UnlockSource(locks[i]); uerr != nil {
				logger.Error("defer unlock 失败: %s", uerr.Error())
			}
			locks[i].Close()
		}
	}()

	for _, ep := range p.SourceEndpoints {
		scope := ep.SyncScope
		if scope == nil || scope.IsEmpty() {
			scope = p.SyncScope
		}
		var useLockTables []dtsutil.TableItem
		if len(p.LockTables) > 0 {
			useLockTables = p.LockTables
		}
		logger.Info("源端 %s:%d 开始展开并加锁 source_name=%s", ep.Host, ep.Port, ep.SourceName)
		sl, lerr := dtsutil.LockSourceTables(ep, scope, useLockTables)
		if lerr != nil {
			return lerr
		}
		locks = append(locks, sl)
		logger.Info("源端 %s:%d 已持有 %d 张表读锁", ep.Host, ep.Port, len(sl.Tables))
	}

	// 加锁后立刻拍 master 快照；后续轮询 syncer>=快照（失败则 unlock via defer，禁止 stop）
	snapResp, ferr := dtsutil.FetchTaskStatus(p.DtsMasterAddr, p.TaskName, 30)
	if ferr != nil {
		return fmt.Errorf("加锁后拉取 status 失败，无法建立位点快照（不执行 stop）: %w", ferr)
	}
	lockSnapshots, serr := dtsutil.BuildLockMasterSnapshots(snapResp.Data)
	if serr != nil {
		return fmt.Errorf("建立加锁位点快照失败（不执行 stop）: %w", serr)
	}
	for src, coord := range lockSnapshots {
		logger.Info("加锁位点快照 source=%s binlog=(%s, %d)", src, coord.File, coord.Position)
	}

	statusItems, perr := dtsutil.PollUntilCaughtUp(
		func() ([]dtsutil.TaskStatusItem, error) {
			resp, ferr := dtsutil.FetchTaskStatus(p.DtsMasterAddr, p.TaskName, 30)
			if ferr != nil {
				return nil, ferr
			}
			return resp.Data, nil
		},
		lockSnapshots,
		p.CatchupRecheck,
		p.catchupPollMax(),
		func() { time.Sleep(catchupPollInterval) },
	)
	if perr != nil {
		return fmt.Errorf("持锁复核追平失败（不执行 stop，将 unlock）: %w", perr)
	}

	logger.Info("持锁复核通过，开始停止任务 task=%s", p.TaskName)
	if err := dtsutil.StopTaskWhileLocked(p.DtsMasterAddr, p.TaskName); err != nil {
		return fmt.Errorf("持锁后停止 DTS 任务失败（将 unlock）: %w", err)
	}

	// 尽量再采一次停任务后的位点；失败则回退持锁复核时的快照
	finalItems := statusItems
	if resp, ferr := dtsutil.FetchTaskStatus(p.DtsMasterAddr, p.TaskName, 30); ferr != nil {
		logger.Warn("停任务后再次拉取 status 失败，使用持锁复核快照: %s", ferr.Error())
	} else if len(resp.Data) > 0 {
		finalItems = resp.Data
	}

	out := dtsutil.BuildPositionOutput(p.TaskName, finalItems)
	if err := components.PrintOutputCtx(out); err != nil {
		return fmt.Errorf("输出位点 JSON 失败: %w", err)
	}
	logger.Info("DTS cutover 完成: task=%s sources=%d", p.TaskName, len(out.Sources))
	return nil
}
