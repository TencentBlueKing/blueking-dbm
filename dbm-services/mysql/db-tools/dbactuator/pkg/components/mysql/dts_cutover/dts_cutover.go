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
// 预检（源连通/表存在/任务可查）→ 源端迁移表读锁 → 拍 master 位点快照并持锁轮询追平 → Master HTTP API stop → 采位点 → 源端 unlock。
// 持锁追平条件：SBM==0 且 syncer≥加锁瞬间 master 快照（不用实时 master≥syncer）。
// 本期不对目标端加锁，不做域名/Proxy 切换。停任务与查状态统一走 Master OpenAPI。
package dts_cutover

import (
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
)

const (
	defaultCatchupRecheck = 3
	defaultCatchupPollMax = 300
	catchupPollInterval   = 1 * time.Second
)

// Comp DTS cutover 组件。
type Comp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *Params                  `json:"extend"`
}

// Params Flow → actuator payload。
type Params struct {
	DtsMasterAddr   string           `json:"dts_master_addr" validate:"required"`
	DeployPath      string           `json:"deploy_path"` // 可选；停任务已改走 API，不再依赖本机 dmctl
	TaskName        string           `json:"task_name" validate:"required"`
	SourceEndpoints []SourceEndpoint `json:"source_endpoints" validate:"required,gt=0,dive"`
	SyncScope       *SyncScope       `json:"sync_scope"`
	LockTables      []TableItem      `json:"lock_tables"`
	// CatchupRecheck：连续通过持锁快照追平的次数，默认 3
	CatchupRecheck int `json:"catchup_recheck"`
	// CatchupPollMax：持锁轮询最大次数（含首次），默认 300；间隔 1s
	CatchupPollMax int `json:"catchup_poll_max"`
	// ApiTimeoutSec：stop API 超时；兼容旧字段 dmctl_timeout_sec
	ApiTimeoutSec   int `json:"api_timeout_sec"`
	DmctlTimeoutSec int `json:"dmctl_timeout_sec"` // deprecated: 同 ApiTimeoutSec
	// ChecksumPassed：编排侧已完成数据校验（部分同步一致性靠 checksum）
	ChecksumPassed bool `json:"checksum_passed"`
	// SkipChecksum：单据明确跳过校验时为 true；否则必须 ChecksumPassed
	SkipChecksum bool `json:"skip_checksum"`
}

// SourceEndpoint 源端连接信息（临时账号；连接发起方 = dts-master）。
type SourceEndpoint struct {
	Host       string     `json:"host" validate:"required"`
	Port       int        `json:"port" validate:"required,gt=0"`
	User       string     `json:"user" validate:"required"`
	Password   string     `json:"password" validate:"required"`
	SourceName string     `json:"source_name"`
	SyncScope  *SyncScope `json:"sync_scope"`
}

// Example payload 示例（IP 使用 127.0.0.x）。
func (c *Comp) Example() interface{} {
	return Comp{
		Params: &Params{
			DtsMasterAddr: "127.0.0.2:18301",
			DeployPath:    "/data/dts/demo",
			TaskName:      "task-a",
			SourceEndpoints: []SourceEndpoint{
				{
					Host:       "127.0.0.10",
					Port:       20000,
					User:       "u",
					Password:   "p",
					SourceName: "src1",
					SyncScope: &SyncScope{
						DoDBs: []string{"app"},
					},
				},
			},
			SyncScope: &SyncScope{
				DoDBs: []string{"app"},
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
	// 部分同步必须先有 checksum（或显式 skip）才能 cutover
	if !p.SkipChecksum && !p.ChecksumPassed {
		return fmt.Errorf("cutover 拒绝执行：checksum 尚未通过（部分同步依赖校验结果；请确认编排先完成数据校验）")
	}
	return nil
}

// Run 执行切换主路径（假定 Steps 已完成 Init/PreCheck；此处 Init 幂等兜底）。
func (c *Comp) Run() error {
	if err := c.Init(); err != nil {
		return err
	}
	p := c.Params
	if p.SkipChecksum {
		logger.Info("单据跳过 checksum，持锁复核按 SBM=0 且 syncer>=加锁 master 快照")
	} else {
		logger.Info("checksum 已通过，持锁复核按 SBM=0 且 syncer>=加锁 master 快照")
	}

	locks := make([]*SourceLockConn, 0, len(p.SourceEndpoints))
	defer func() {
		for i := len(locks) - 1; i >= 0; i-- {
			if uerr := UnlockSource(locks[i]); uerr != nil {
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
		var useLockTables []TableItem
		if len(p.LockTables) > 0 {
			useLockTables = p.LockTables
		}
		logger.Info("源端 %s:%d 开始展开并加锁 source_name=%s", ep.Host, ep.Port, ep.SourceName)
		sl, lerr := LockSourceTables(ep, scope, useLockTables)
		if lerr != nil {
			return lerr
		}
		locks = append(locks, sl)
		logger.Info("源端 %s:%d 已持有 %d 张表读锁", ep.Host, ep.Port, len(sl.Tables))
	}

	// 加锁后立刻拍 master 快照；后续轮询 syncer>=快照（失败则 unlock via defer，禁止 stop）
	snapResp, ferr := FetchTaskStatus(p.DtsMasterAddr, p.TaskName, 30)
	if ferr != nil {
		return fmt.Errorf("加锁后拉取 status 失败，无法建立位点快照（不执行 stop）: %w", ferr)
	}
	lockSnapshots, serr := BuildLockMasterSnapshots(snapResp.Data)
	if serr != nil {
		return fmt.Errorf("建立加锁位点快照失败（不执行 stop）: %w", serr)
	}
	for src, coord := range lockSnapshots {
		logger.Info("加锁位点快照 source=%s master=(%s, %d)", src, coord.File, coord.Position)
	}

	var statusItems []TaskStatusItem
	consecutive := 0
	pollMax := p.catchupPollMax()
	var lastCatchupErr error
	for attempt := 0; attempt < pollMax; attempt++ {
		if attempt > 0 {
			time.Sleep(catchupPollInterval)
		}
		resp, ferr := FetchTaskStatus(p.DtsMasterAddr, p.TaskName, 30)
		if ferr != nil {
			return fmt.Errorf("持锁复核追平失败（不执行 stop）: %w", ferr)
		}
		statusItems = resp.Data
		if cerr := CheckSnapshotCatchup(statusItems, lockSnapshots); cerr != nil {
			consecutive = 0
			lastCatchupErr = cerr
			logger.Warn("持锁复核未追平 attempt=%d/%d: %s", attempt+1, pollMax, cerr.Error())
			continue
		}
		consecutive++
		logger.Info("持锁复核追平通过 (%d/%d) attempt=%d/%d", consecutive, p.CatchupRecheck, attempt+1, pollMax)
		if consecutive >= p.CatchupRecheck {
			break
		}
	}
	if consecutive < p.CatchupRecheck {
		if lastCatchupErr == nil {
			lastCatchupErr = fmt.Errorf("连续通过次数不足: got=%d want=%d", consecutive, p.CatchupRecheck)
		}
		return fmt.Errorf("持锁复核超时（将 unlock，不执行 stop）: %w", lastCatchupErr)
	}

	if err := StopTask(p.DtsMasterAddr, p.TaskName, p.ApiTimeoutSec, nil); err != nil {
		return fmt.Errorf("持锁后停止 DTS 任务失败（将 unlock）: %w", err)
	}

	// 尽量再采一次停任务后的位点；失败则回退持锁复核时的快照
	finalItems := statusItems
	if resp, ferr := FetchTaskStatus(p.DtsMasterAddr, p.TaskName, 30); ferr != nil {
		logger.Warn("停任务后再次拉取 status 失败，使用持锁复核快照: %s", ferr.Error())
	} else if len(resp.Data) > 0 {
		finalItems = resp.Data
	}

	out := BuildPositionOutput(p.TaskName, finalItems)
	if err := components.PrintOutputCtx(out); err != nil {
		return fmt.Errorf("输出位点 JSON 失败: %w", err)
	}
	logger.Info("DTS cutover 完成: task=%s sources=%d", p.TaskName, len(out.Sources))
	return nil
}
