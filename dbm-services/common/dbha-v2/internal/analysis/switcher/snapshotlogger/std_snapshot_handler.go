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

package snapshotlogger

import (
	"encoding/json"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// StdSnapshotHandler is a handler that writes switch log records to standard output.
type StdSnapshotHandler struct {
	logger logger.Logger
}

// NewStdSnapshotHandler creates a new StdSnapshotHandler.
func NewStdSnapshotHandler(logger logger.Logger) *StdSnapshotHandler {
	return &StdSnapshotHandler{
		logger: logger,
	}
}

// Open this function does nothing, only for interface
func (hdl *StdSnapshotHandler) Open() error {
	return nil
}

// Close this function does nothing, only for interface
func (hdl *StdSnapshotHandler) Close() {
}

// PreSwitchLog logs the snapshot before the switch executes.
func (hdl *StdSnapshotHandler) PreSwitchLog(record *SwitchingSnapshotData) error {
	if hdl.logger == nil {
		return nil
	}

	if record == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "before switching snapshot record for std is nil")
	}
	if record.DbSwitchingSnapshotLog == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "dbSwitchingSnapshotLog is nil for before std switching snapshot")
	}

	payload := StdSwitchingSnapshotData{
		StartTime:            record.DbSwitchingSnapshotLog.StartTime,
		BkBizID:              record.DbSwitchingSnapshotLog.BkBizID,
		BkCloudID:            record.DbSwitchingSnapshotLog.BkCloudID,
		Reason:               record.DbSwitchingSnapshotLog.Reason,
		DbType:               record.DbSwitchingSnapshotLog.DbType,
		ActionScope:          record.DbSwitchingSnapshotLog.ActionScope,
		Action:               record.DbSwitchingSnapshotLog.Action.String(),
		StrategyJSON:         record.StrategyJSON,
		StrategiesJSON:       record.StrategiesJSON,
		FailureInstancesJSON: record.FailureInstancesJSON,
		OriginInstancesJSON:  record.OriginInstancesJSON,
		MetadataSetJSON:      record.MetadataSetJSON,
	}

	body, err := json.Marshal(&payload)
	if err != nil {
		return gerrors.Newf(gerrors.InvalidJson,
			"failed to marshal before switching snapshot payload, switchId: %s, errmsg: %s",
			record.DbSwitchingSnapshotLog.SwitchID, err)
	}

	// the log type column is simply the snapshot action (pre-switch / notify)
	hdl.logger.Info("%s\t%s\t%s", record.DbSwitchingSnapshotLog.SwitchID,
		record.DbSwitchingSnapshotLog.Action.String(), string(body))

	return nil
}

// PostSwitchLog logs the snapshot after the switch executes.
func (hdl *StdSnapshotHandler) PostSwitchLog(record *SwitchingSnapshotData) error {
	if hdl.logger == nil {
		return nil
	}

	if record == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "after switching snapshot record for std is nil")
	}
	if record.DbSwitchingSnapshotLog == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "dbSwitchingSnapshotLog is nil for after std switching snapshot")
	}

	payload := StdSwitchingSnapshotData{
		FinishedTime:  record.DbSwitchingSnapshotLog.FinishedTime,
		Result:        record.DbSwitchingSnapshotLog.Result,
		Status:        record.DbSwitchingSnapshotLog.Status.String(),
		Action:        record.DbSwitchingSnapshotLog.Action.String(),
		InstancesJSON: record.InstancesJSON,
	}

	body, err := json.Marshal(&payload)
	if err != nil {
		return gerrors.Newf(gerrors.InvalidJson,
			"failed to marshal after switching snapshot payload, switchId: %s, errmsg: %s",
			record.DbSwitchingSnapshotLog.SwitchID, err)
	}

	hdl.logger.Info("%s\t%s\t%s", record.DbSwitchingSnapshotLog.SwitchID,
		record.DbSwitchingSnapshotLog.Action.String(), string(body))

	return nil
}
