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

// Package redisparse registers the Redis status parser (Processer).
package redisparse

import (
	"encoding/json"
	"fmt"
	"strings"

	"dbm-services/common/dbha-v2/internal/analysis/parser"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ parser.Processer = (*Status)(nil)

var errInvalidRedisStatus = gerrors.Newf(gerrors.InvalidParameter, "invalid Redis status")

// redisRoleMaster is the master role value reported by INFO Replication.
const redisRoleMaster = "master"

// Status parses Redis probe status payloads.
type Status struct{}

// Process parses one Redis raw status payload into a DB event.
//
// Rules (aligned with the detection design):
//   - any probe item in State=failed → a detect-failure DB event;
//   - master heartbeat whose SelectResult / SetResult lacks the expected content
//     → a defensive detect-failure DB event (strings.Contains, aligned with v1);
//   - otherwise (slave, proxy read-check, or all-nil items) → nil (no event).
//
// A nil event is important: the all-nil case covers shouldSkipStorage, open
// connection/auth failure, and command auth failure — those are reported via
// data.Events rather than via the status payload.
func (s *Status) Process(task json.RawMessage) (*haprobe.DbEvent, error) {
	var redisStatus haprobe.RedisStatus
	if err := json.Unmarshal(task, &redisStatus); err != nil {
		logger.Warn("failed to unmarshal Redis status, errmsg: %s", err)
		return nil, errInvalidRedisStatus
	}

	if redisStatus.ReplicationStatus == nil &&
		redisStatus.HeartbeatStatus == nil &&
		redisStatus.ReadCheckStatus == nil {
		return nil, nil
	}

	if event := failedEvent(&redisStatus); event != nil {
		return event, nil
	}

	if event := heartbeatDefensiveEvent(&redisStatus); event != nil {
		return event, nil
	}

	return nil, nil
}

// failedEvent returns a detect-failure event for the first probe item in State=failed.
func failedEvent(r *haprobe.RedisStatus) *haprobe.DbEvent {
	switch {
	case r.ReplicationStatus != nil && r.ReplicationStatus.State == haprobe.RedisStateFailed:
		return detectFailureEvent(r.ReplicationStatus.FailureReason)
	case r.HeartbeatStatus != nil && r.HeartbeatStatus.State == haprobe.RedisStateFailed:
		return detectFailureEvent(r.HeartbeatStatus.FailureReason)
	case r.ReadCheckStatus != nil && r.ReadCheckStatus.State == haprobe.RedisStateFailed:
		return detectFailureEvent(r.ReadCheckStatus.FailureReason)
	default:
		return nil
	}
}

// heartbeatDefensiveEvent guards against the probe phase changing in a way that
// marks the heartbeat ok while the raw reply no longer carries the expected
// content. It mirrors v1's strings.Contains checks.
func heartbeatDefensiveEvent(r *haprobe.RedisStatus) *haprobe.DbEvent {
	if r.HeartbeatStatus == nil || r.HeartbeatStatus.State != haprobe.RedisStateOk {
		return nil
	}
	if r.ReplicationStatus == nil || r.ReplicationStatus.Role != redisRoleMaster {
		return nil
	}

	if !strings.Contains(r.HeartbeatStatus.SelectResult, "OK") {
		return detectFailureEvent(fmt.Sprintf("redis select rsp[%s] type is not ok", r.HeartbeatStatus.SelectResult))
	}
	if !strings.Contains(r.HeartbeatStatus.SetResult, "OK") &&
		!strings.Contains(r.HeartbeatStatus.SetResult, "MOVED") {
		return detectFailureEvent(fmt.Sprintf("set check failed, rsp[%s]", r.HeartbeatStatus.SetResult))
	}

	return nil
}

// detectFailureEvent builds a detect-failure DB event with the given reason message.
// The endpoint / bk_cloud_id are filled by StatusParser from the reporting instance.
func detectFailureEvent(message string) *haprobe.DbEvent {
	return &haprobe.DbEvent{
		Name:       haprobe.DbEventNameDetectFailure,
		Reason:     haprobe.DbEventNameReasonConnectionException,
		DbTypeName: haprobe.DbTypeRedis,
		Message:    message,
	}
}

func init() {
	parser.Register(haprobe.DbTypeRedis, &Status{})
}
