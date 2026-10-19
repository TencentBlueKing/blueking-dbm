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
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/detector"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// sshCheckFailedStatus matches v1 constvar.SSHCheckFailed in
// dbha/ha-module/constvar/constant.go.
const sshCheckFailedStatus = "SSH_check_failed"

// redisAuthFailedStatus matches v1 constvar.RedisAuthFailed, reported by the v1 agent when
// the redis detection fails on authentication.
const redisAuthFailedStatus = "Redis_auth_failed"

// emptyInstanceRole matches v1 GetDBRole when the detect role is empty.
const emptyInstanceRole = "N/A"

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
	fillDetectV1Dimensions(monitorEvent, resp.Meta)

	logger.Info("the workflow triggers an alarm, db-inst: %d:%s:%d content: %s",
		resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port, content)

	if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
		logger.Warn("failed to post the alarm event to BkMonitor, errmsg: %s", err)
	}
}

// TriggerWithEvent sends a notification for the event before liveness double-check.
// meta carries the instance metadata used by the v2 and v1 dimensions; a nil meta only
// skips those dimensions and the notification is still posted.
func (n *AlarmNotifier) TriggerWithEvent(event *haprobe.DbEvent, meta *hamodel.DbmMetadata) {
	if event == nil || event.Endpoint == nil {
		logger.Warn("skip notification: nil event or endpoint")
		return
	}

	target := instanceKey(event.BkCloudID, event.Endpoint.Host, event.Endpoint.Port)
	monitorEvent := &monitor.EventData{
		Name:      event.Name.String(),
		Target:    target,
		Timestamp: uint64(time.Now().UnixMilli()),
	}

	monitorEvent.Content.Content = event.Message

	monitorEvent.Dimension.BkCloudId = event.BkCloudID
	monitorEvent.Dimension.IP = event.Endpoint.Host
	monitorEvent.Dimension.Port = event.Endpoint.Port
	monitorEvent.Dimension.DbTypeName = event.DbTypeName
	monitorEvent.Dimension.DbEventName = event.Name
	monitorEvent.Dimension.DbEventNameReason = event.Reason.Str()

	if meta == nil {
		logger.Warn("skip the meta dimensions: nil meta, db-inst: %s", target)
	} else {
		monitorEvent.Dimension.BkBizId = meta.BkBizID
		monitorEvent.Dimension.DbClusterType = meta.ClusterType
		monitorEvent.Dimension.DbMachineType = meta.MachineType
		fillDetectV1Dimensions(monitorEvent, meta)
	}

	logger.Info("send a notification before double-check, db-inst: %s, event: %s, content: %s",
		target, event.Name, event.Message)

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

// fillDetectV1Dimensions writes the v1 detect dimensions onto a detector alarm.
// meta must be non-nil. An empty instance role is written as N/A.
// status is SSH_check_failed for dbha_doublecheck_ssh_fail and Redis_auth_failed for
// dbha_detect_redis_auth_fail, matching the v1 agent reportMonitor statuses.
// idc is left unset because v1 detect events do not carry that key.
func fillDetectV1Dimensions(event *monitor.EventData, meta *hamodel.DbmMetadata) {
	event.Dimension.BkCloudId = meta.BkCloudID
	event.Dimension.SwitchInfoBkBizIdV1 = strconv.Itoa(meta.BkBizID)
	event.Dimension.SwitchInfoServerIpV1 = meta.IP
	event.Dimension.SwitchInfoServerPortV1 = meta.Port
	event.Dimension.SwitchInfoClusterDomainV1 = meta.Cluster
	event.Dimension.SwitchInfoMachineTypeV1 = string(meta.MachineType)
	event.Dimension.SwitchInfoDetectClusterType = string(meta.ClusterType)
	event.Dimension.SwitchInfoInstanceRoleV1 = detectInstanceRole(meta.InstanceRole)

	switch event.Name {
	case haprobe.DbEventNameDoubleCheckSshFailureV1.String():
		event.Dimension.SwitchInfoStatusV1 = sshCheckFailedStatus
	case haprobe.DbEventNameDetectRedisAuthFailureV1.String():
		event.Dimension.SwitchInfoStatusV1 = redisAuthFailedStatus
	}
}

// detectInstanceRole returns the v1 detect instance role.
// An empty role becomes N/A, matching GetDBRole.
func detectInstanceRole(role haprobe.DbmMetadataInstanceRole) string {
	if role == "" {
		return emptyInstanceRole
	}
	return string(role)
}
