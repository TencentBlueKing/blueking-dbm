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
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/detector"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// DetectorHandler processes detector responses and runs liveness double-check,
// then triggers switching via SwitchExecutor.
type DetectorHandler struct {
	alarm          *AlarmNotifier
	switchExecutor *SwitchExecutor
}

// NewDetectorHandler creates a DetectorHandler.
func NewDetectorHandler(alarm *AlarmNotifier, switchExecutor *SwitchExecutor) *DetectorHandler {
	return &DetectorHandler{alarm: alarm, switchExecutor: switchExecutor}
}

// ProcessResponse handles a single detector response: alarms and returns ErrDetectorFailure if switching is needed.
func (h *DetectorHandler) ProcessResponse(resp *detector.Response) error {
	if resp.Err == detector.ErrDetectorCreateSshConnection {
		resp.DbEventName = haprobe.DbEventNameDoubleCheckSshFailureV1
		resp.DbEventNameReason = haprobe.DbEventNameReasonConnectionException

		content := fmt.Sprintf("failed to dial the remote host with SSH, host: %d:%s:%d",
			resp.Meta.BkCloudID, resp.Meta.IP, config.Cfg.Detector.Ssh.Port)

		h.alarm.TriggerWithDetectorResponse("", "", content, gerrors.Failure.Int(), resp)
		return ErrDetectorFailure
	}

	if resp.Err == detector.ErrDetectorCreateSshSession {
		resp.DbEventName = haprobe.DbEventNameDoubleCheckSshFailureV1
		resp.DbEventNameReason = haprobe.DbEventNameReasonConnectionException

		content := fmt.Sprintf("failed to create SSH session with the remote host, host: %d:%s:%d",
			resp.Meta.BkCloudID, resp.Meta.IP, config.Cfg.Detector.Ssh.Port)

		h.alarm.TriggerWithDetectorResponse("", "", content, gerrors.Failure.Int(), resp)
		return ErrDetectorFailure
	}

	if resp.Err != nil {
		h.alarm.TriggerWithDetectorResponse("", "", resp.Err.Error(), gerrors.Failure.Int(), resp)
		return nil
	}

	if resp.SshResp.ExitCode != 0 {
		content := fmt.Sprintf("%s, errmsg: %s", resp.SshResp.Data, resp.SshResp.ErrMsg)
		h.alarm.TriggerWithDetectorResponse("", "", content, resp.SshResp.ExitCode, resp)
		return nil
	}

	// Parse the probe health.
	var health process.HealthInfo
	err := json.Unmarshal([]byte(resp.SshResp.Data), &health)
	if err != nil {
		h.alarm.TriggerWithDetectorResponse("", "", err.Error(), gerrors.Failure.Int(), resp)
		return nil
	}

	content := fmt.Sprintf("pid: %d proc name: %s status: %s", health.Pid, health.ProcName, health.Status)
	if health.Pid == process.InvalidPid {
		content = health.ErrMsg
	} else {
		// Probe is running, but there are no target database metrics.
		content = fmt.Sprintf("%s, db: %s:%d", content, resp.Meta.IP, resp.Meta.Port)
		resp.DbEventName = haprobe.DbEventNameDetectFailure
		resp.DbEventNameReason = haprobe.DbEventNameReasonNoTarget
	}

	h.alarm.TriggerWithDetectorResponse(health.ProcName, health.Status, content, resp.SshResp.ExitCode, resp)
	return nil
}

// LivenessDoubleCheck runs remote detection on missed instances, collects failures, and triggers switching per group.
func (h *DetectorHandler) LivenessDoubleCheck(missedInsts []detector.DoubleCheckTask) {
	remoteDetector := detector.Detector{}

	if err := remoteDetector.Detect(missedInsts); err != nil {
		logger.Warn("failed to detect remote db-insts, errmsg: %s", err)
		return
	}

	resps := remoteDetector.WaitResponses()

	collector := NewFailureCollector()

	for idx, resp := range resps {
		logger.Debug("idx: %d host: %s:%d resp: %p", idx, resp.Meta.IP, resp.Meta.Port, resp)
		err := h.ProcessResponse(resp)
		if err == nil {
			continue
		}

		if err != ErrDetectorFailure {
			instId := instanceKey(resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port)
			logger.Warn("failed to process detector response, inst: %s, errmsg: %s", instId, err)
			continue
		}

		collector.Add(resp)
	}

	if collector.Empty() {
		return
	}

	for _, group := range collector.Groups() {
		logger.Debug("cloudId: %d, dbType: %s, instances: %d, ips: %v",
			group.BkCloudID, group.DbType, len(group.Instances), group.IPs())

		req := h.switchExecutor.CreateRequestWithGroup(group)
		if req == nil {
			continue
		}

		if !req.HasDbInstMetadata() {
			logger.Warn("no db inst metadata, dbType: %s, cloudId: %d, instances: %d",
				group.DbType, group.BkCloudID, len(group.Instances))
			continue
		}

		matched, strategy := h.switchExecutor.MatchStrategyForGroup(group)
		if !matched {
			logger.Info("no matching switching strategy, skip switching, cloudId: %d, dbType: %s, event: %s, reason: %s",
				group.BkCloudID, group.DbType, group.EventName, group.EventNameReason.Str())
			continue
		}

		if strategy.Action != hamodel.ActionTypeSwitch {
			logger.Info("strategy action is %s, skip switching, strategy: %s, cloudId: %d, dbType: %s",
				strategy.Action, strategy.Name, group.BkCloudID, group.DbType)
			continue
		}

		logger.Debug("trigger switching by strategy %s, dbType: %s, cloudId: %d, instances: %d",
			strategy.Name, group.DbType, group.BkCloudID, len(group.Instances))

		// TODO: set the action scope and swicth ID of the switch request properly
		req.ActionScope = hamodel.ActionScopeTypeHost
		req.SwitchID = "test_switch_id"
		h.switchExecutor.TriggerSwitching(group.DbType, req)
	}
}
