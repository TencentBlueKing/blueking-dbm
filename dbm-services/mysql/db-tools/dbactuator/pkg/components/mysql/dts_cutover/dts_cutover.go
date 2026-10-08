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
	DtsMasterAddr   string           `json:"dts_master_addr" validate:"required"`
	DeployPath      string           `json:"deploy_path"` // 可选；停任务已改走 API，不再依赖本机 dmctl
	TaskName        string           `json:"task_name" validate:"required"`
	SourceEndpoints []SourceEndpoint `json:"source_endpoints" validate:"required,gt=0,dive"`
	SyncScope       *SyncScope       `json:"sync_scope"`
	LockTables      []TableItem      `json:"lock_tables"`
	// CatchupRecheck：连续通过持锁快照追平的次数，默认 3
	CatchupRecheck int `json:"catchup_recheck"`
	// CatchupPollMax：持锁复核最大次数（含首次），默认 60；间隔 0.5s
	CatchupPollMax int `json:"catchup_poll_max"`
	// ApiTimeoutSec：stop API 超时；兼容旧字段 dmctl_timeout_sec
	ApiTimeoutSec   int `json:"api_timeout_sec"`
	DmctlTimeoutSec int `json:"dmctl_timeout_sec"` // deprecated: 同 ApiTimeoutSec
	// 编排透传。cutover 不读校验结果，也不据此改变追平。
	ChecksumPassed bool `json:"checksum_passed"`
	SkipChecksum   bool `json:"skip_checksum"`
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
						DoDBs:    []string{"app"},
						DoTables: []TableItem{{Schema: "*", Table: "*"}},
					},
				},
			},
			SyncScope: &SyncScope{
				DoDBs:    []string{"app"},
				DoTables: []TableItem{{Schema: "*", Table: "*"}},
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
	logger.Info("持锁复核按 SBM=0 且 syncer>=加锁 master 快照 skip_checksum=%t", p.SkipChecksum)

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

	statusItems, perr := pollUntilCaughtUp(
		func() ([]TaskStatusItem, error) {
			resp, ferr := FetchTaskStatus(p.DtsMasterAddr, p.TaskName, 30)
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
		return perr
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

type catchupPollAction int

const (
	catchupPollPass catchupPollAction = iota
	catchupPollRetry
	catchupPollAbort
)

// taskReportError 单元失败时 worker 把 stage 写成 Paused，并把错误放进 error_msg。
// 人工暂停也是 Paused，但 error_msg 为空，继续等追平。
// InvalidStage 是占位，正常状态不会出现，见到就退出。
func taskReportError(items []TaskStatusItem) error {
	for _, item := range items {
		stage := TaskStage(strings.TrimSpace(string(item.Stage)))
		src := statusSourceKey(item)
		msg := strings.TrimSpace(item.ErrorMsg)
		switch stage {
		case TaskStageInvalidStage:
			if msg != "" {
				return fmt.Errorf("source %s 任务错误: %s", src, msg)
			}
			return fmt.Errorf("source %s 任务阶段异常: stage=%s", src, stage)
		case TaskStagePaused:
			if msg == "" {
				continue
			}
			return fmt.Errorf("source %s 任务错误: %s", src, msg)
		}
	}
	return nil
}

func decideCatchupPoll(items []TaskStatusItem, snapshots map[string]BinlogCoord) (catchupPollAction, error) {
	if err := taskReportError(items); err != nil {
		return catchupPollAbort, err
	}
	if err := CheckSnapshotCatchup(items, snapshots); err != nil {
		return catchupPollRetry, err
	}
	return catchupPollPass, nil
}

// sourcesQuietEnoughToLock 加锁前只看延迟和 blocking_ddls，不拿实时 master 跟 syncer 比。
func sourcesQuietEnoughToLock(items []TaskStatusItem) error {
	if len(items) == 0 {
		return fmt.Errorf("任务状态为空")
	}
	for _, item := range items {
		src := statusSourceKey(item)
		if item.SyncStatus == nil {
			return fmt.Errorf("source %s 缺少 sync_status", src)
		}
		ss := item.SyncStatus
		if len(ss.BlockingDDLs) > 0 {
			return fmt.Errorf("source %s 存在 blocking_ddls: %v", src, ss.BlockingDDLs)
		}
		if ss.SecondsBehindMaster != 0 {
			return fmt.Errorf("source %s 未追平: sbm=%d", src, ss.SecondsBehindMaster)
		}
	}
	return nil
}

func decideReadyBeforeLock(items []TaskStatusItem) (catchupPollAction, error) {
	if err := taskReportError(items); err != nil {
		return catchupPollAbort, err
	}
	if err := validateTaskRunning(&TaskStatusListResponse{Data: items}); err != nil {
		return catchupPollAbort, err
	}
	if err := sourcesQuietEnoughToLock(items); err != nil {
		return catchupPollRetry, err
	}
	return catchupPollPass, nil
}

// pollReadyBeforeLock 在 FLUSH 之前等到各源 SBM==0。报错或非 Running 立刻失败，不进入加锁。
func pollReadyBeforeLock(
	fetch func() ([]TaskStatusItem, error),
	pollMax int,
	sleep func(),
) error {
	if pollMax < 1 {
		pollMax = 1
	}
	var lastErr error
	for attempt := 0; attempt < pollMax; attempt++ {
		if attempt > 0 && sleep != nil {
			sleep()
		}
		items, ferr := fetch()
		if ferr != nil {
			return fmt.Errorf("预检查询任务 status 失败: %w", ferr)
		}
		action, cerr := decideReadyBeforeLock(items)
		switch action {
		case catchupPollAbort:
			return fmt.Errorf("预检发现 DTS 任务不可切换（未加锁）: %w", cerr)
		case catchupPollRetry:
			lastErr = cerr
			logger.Warn("预检尚未适合加锁 attempt=%d/%d: %s", attempt+1, pollMax, cerr.Error())
			continue
		default:
			logger.Info("预检适合加锁 attempt=%d/%d", attempt+1, pollMax)
			return nil
		}
	}
	if lastErr == nil {
		lastErr = fmt.Errorf("未观察到适合加锁的状态")
	}
	return fmt.Errorf("预检追平超时（未加锁）: %w", lastErr)
}

func pollUntilCaughtUp(
	fetch func() ([]TaskStatusItem, error),
	snapshots map[string]BinlogCoord,
	recheck int,
	pollMax int,
	sleep func(),
) ([]TaskStatusItem, error) {
	if recheck < 1 {
		recheck = 1
	}
	if pollMax < 1 {
		pollMax = 1
	}
	var statusItems []TaskStatusItem
	consecutive := 0
	var lastCatchupErr error
	for attempt := 0; attempt < pollMax; attempt++ {
		if attempt > 0 && sleep != nil {
			sleep()
		}
		items, ferr := fetch()
		if ferr != nil {
			return nil, fmt.Errorf("持锁复核追平失败（不执行 stop）: %w", ferr)
		}
		statusItems = items
		action, cerr := decideCatchupPoll(items, snapshots)
		switch action {
		case catchupPollAbort:
			return nil, fmt.Errorf("持锁复核发现 DTS 任务报错（不执行 stop，将 unlock）: %w", cerr)
		case catchupPollRetry:
			consecutive = 0
			lastCatchupErr = cerr
			logger.Warn("持锁复核未追平 attempt=%d/%d: %s", attempt+1, pollMax, cerr.Error())
			continue
		default:
			consecutive++
			logger.Info("持锁复核追平通过 (%d/%d) attempt=%d/%d", consecutive, recheck, attempt+1, pollMax)
			if consecutive >= recheck {
				return statusItems, nil
			}
		}
	}
	if lastCatchupErr == nil {
		lastCatchupErr = fmt.Errorf("连续通过次数不足: got=%d want=%d", consecutive, recheck)
	}
	return nil, fmt.Errorf("持锁复核超时（将 unlock，不执行 stop）: %w", lastCatchupErr)
}
