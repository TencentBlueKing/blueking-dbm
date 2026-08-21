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
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/detector"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// DetectorHandler processes detector responses and runs liveness double-check,
// then pushes confirmed failure instances into the sliding window for subsequent pop-switch.
type DetectorHandler struct {
	alarm       *AlarmNotifier
	windowMgr   *BizWindowManager
	myServiceID string
}

// NewDetectorHandler creates a DetectorHandler.
func NewDetectorHandler(alarm *AlarmNotifier, windowMgr *BizWindowManager, serviceID string) *DetectorHandler {
	return &DetectorHandler{alarm: alarm, windowMgr: windowMgr, myServiceID: serviceID}
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

	if resp.Err == detector.ErrDetectorSshAuth {
		resp.DbEventName = haprobe.DbEventNameSshAuthFailure
		resp.DbEventNameReason = haprobe.DbEventNameReasonSSHAuthException

		content := fmt.Sprintf("failed to authenticate the remote host with SSH, host: %d:%s:%d",
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

	if resp.SshResp.ErrMsg == detector.ErrDetectorSshTimeout.Error() {
		resp.DbEventName = haprobe.DbEventNameSshTimeout
		resp.DbEventNameReason = haprobe.DbEventNameReasonSshTimeout
		content := fmt.Sprintf("%s, host: %d:%s", resp.SshResp.ErrMsg, resp.Meta.BkCloudID, resp.Meta.IP)
		h.alarm.TriggerWithDetectorResponse("", "", content, resp.SshResp.ExitCode, resp)
		return ErrDetectorFailure
	}

	if resp.SshResp.ExitCode == process.ExitCodeHealthDiskWriteFail {
		resp.DbEventName = haprobe.DbEventNameDiskWriteFailure
		resp.DbEventNameReason = haprobe.DbEventNameReasonDiskWriteException
		content := fmt.Sprintf("disk write verification failed, host: %d:%s, errmsg: %s",
			resp.Meta.BkCloudID, resp.Meta.IP, resp.SshResp.Data)
		h.alarm.TriggerWithDetectorResponse("", "", content, resp.SshResp.ExitCode, resp)
		return ErrDetectorFailure
	}

	if resp.SshResp.ExitCode == process.ExitCodeHealthUptimeFail {
		resp.DbEventName = haprobe.DbEventNameUptimeFailure
		resp.DbEventNameReason = haprobe.DbEventNameReasonUptimeException
		content := fmt.Sprintf("uptime collection failed, host: %d:%s, errmsg: %s",
			resp.Meta.BkCloudID, resp.Meta.IP, resp.SshResp.Data)
		h.alarm.TriggerWithDetectorResponse("", "", content, resp.SshResp.ExitCode, resp)
		return ErrDetectorFailure
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

// LivenessDoubleCheck runs remote detection on missed instances, collects failures,
// and pushes confirmed failure instances into the sliding window.
// Strategy matching and switching are handled asynchronously by the PopAndSwitch loop.
func (h *DetectorHandler) LivenessDoubleCheck(bizId int, missedInsts []detector.DoubleCheckTask) {
	remoteDetector := detector.Detector{ServiceID: h.myServiceID}

	if err := remoteDetector.Detect(missedInsts); err != nil {
		logger.Warn("failed to detect remote db-insts, errmsg: %s", err)
		return
	}

	resps := remoteDetector.WaitResponses()

	now := time.Now()
	pushCount := 0

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

		// Build failure instance info and push into the sliding window
		inst := &FailureInstanceInfo{
			BkCloudID:         resp.Meta.BkCloudID,
			IP:                resp.Meta.IP,
			Port:              resp.Meta.Port,
			BkBizID:           resp.Meta.BkBizID,
			Cluster:           resp.Meta.Cluster,
			ClusterID:         resp.Meta.ClusterID,
			DbType:            resp.DbType,
			EventName:         resp.DbEventName,
			EventNameReason:   resp.DbEventNameReason,
			ClusterType:       resp.Meta.ClusterType,
			MachineType:       resp.Meta.MachineType,
			InstanceRole:      resp.Meta.InstanceRole,
			CheckStartTime:    resp.CheckStartTime,
			CheckFinishedTime: resp.CheckFinishedTime,
		}

		if h.windowMgr.Push(bizId, inst, now) {
			pushCount++
		}
	}

	if pushCount > 0 {
		logger.Info("pushed %d failure instances into the window, bizId: %d", pushCount, bizId)
	}
}
