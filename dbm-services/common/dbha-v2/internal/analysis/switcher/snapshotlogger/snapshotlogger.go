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

// Package snapshotlogger provides different implementations of switching snapshot log
package snapshotlogger

import (
	"encoding/json"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// SwitchSnapshotLogger is the generic interface for writing switching snapshot log records.
type SwitchSnapshotLogger[T any] interface {
	// Open initialize the resource for logging
	Open() error
	// Close recycle the resource for logging
	Close()
	// PreSwitchLog logs the snapshot before the switch executes. Make sure this method is thread-safe.
	PreSwitchLog(record T) error
	// PostSwitchLog logs the snapshot after the switch executes. Make sure this method is thread-safe.
	PostSwitchLog(record T) error
}

type SnapshotLogger = SwitchSnapshotLogger[*SwitchingSnapshotData]

// StdSwitchingSnapshotData is the data structure for switching snapshot logging to standard output.
type StdSwitchingSnapshotData struct {
	StartTime            *time.Time      `json:"start_time,omitempty"`
	FinishedTime         *time.Time      `json:"finished_time,omitempty"`
	BkBizID              int             `json:"bk_biz_id,omitempty"`
	BkCloudID            int             `json:"bk_cloud_id"`
	Reason               string          `json:"reason,omitempty"`
	Result               string          `json:"result,omitempty"`
	Status               string          `json:"status,omitempty"`
	DbType               string          `json:"db_type,omitempty"`
	ActionScope          string          `json:"action_scope,omitempty"`
	Action               string          `json:"action,omitempty"`
	StrategyJSON         json.RawMessage `json:"strategy,omitempty"`
	StrategiesJSON       json.RawMessage `json:"strategies,omitempty"`
	FailureInstancesJSON json.RawMessage `json:"failure_instances,omitempty"`
	MetadataSetJSON      json.RawMessage `json:"metadata_set,omitempty"`
	InstancesJSON        json.RawMessage `json:"instances,omitempty"`
	OriginInstancesJSON  json.RawMessage `json:"origin_instances,omitempty"`
}

// SwitchingSnapshotData is the data structure for switching snapshot logging.
type SwitchingSnapshotData struct {
	StdSwitchingSnapshotData
	DbSwitchingSnapshotLog *hamodel.DbSwitchingSnapshotLog `json:"-"`
	SwSnapshotLogger       logger.Logger                   `json:"-"`
}
