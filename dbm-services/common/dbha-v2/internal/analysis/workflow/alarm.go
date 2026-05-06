/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package workflow

import (
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/detector"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/process"
)

// AlarmNotifier posts alarm events to the monitoring platform.
type AlarmNotifier struct{}

// NewAlarmNotifier creates an AlarmNotifier.
func NewAlarmNotifier() *AlarmNotifier {
	return &AlarmNotifier{}
}

// TriggerWithDetectorResponse posts an alarm event with detector response dimensions.
func (n *AlarmNotifier) TriggerWithDetectorResponse(procName string, status process.Status,
	content string, exitCode int, resp *detector.Response) {
	target := instanceKey(resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port)
	monitorEvent := &monitor.EventData{
		Name:      resp.DbEventName.String(),
		Target:    target,
		Timestamp: uint64(time.Now().UnixMilli()),
	}

	monitorEvent.Content.Content = content

	monitorEvent.Dimension.DetectorExitCode = exitCode
	monitorEvent.Dimension.IP = resp.Meta.IP
	monitorEvent.Dimension.Port = resp.Meta.Port
	monitorEvent.Dimension.BkBizId = resp.Meta.BkBizID
	monitorEvent.Dimension.DbClusterType = resp.Meta.ClusterType
	monitorEvent.Dimension.DbMachineType = resp.Meta.MachineType
	monitorEvent.Dimension.DetectorProcName = procName
	monitorEvent.Dimension.DetectorProcStatus = status
	monitorEvent.Dimension.DbEventName = resp.DbEventName
	monitorEvent.Dimension.DbEventNameReason = resp.DbEventNameReason.Str()

	logger.Info("the workflow triggers an alarm, db-inst: %d:%s:%d content: %s",
		resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port, content)

	if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
		logger.Warn("failed to post the alarm event to BkMonitor, errmsg: %s", err)
	}
}

// TriggerWithBizId posts an alarm event for a business ID.
func (n *AlarmNotifier) TriggerWithBizId(bizId int, content string) {
	target := fmt.Sprintf("BizId: %d", bizId)

	monitorEvent := &monitor.EventData{
		Name:      "",
		Target:    target,
		Timestamp: uint64(time.Now().UnixMilli()),
	}

	monitorEvent.Content.Content = content

	monitorEvent.Dimension.BkBizId = bizId

	if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
		logger.Warn("%s", err)
	}
}
