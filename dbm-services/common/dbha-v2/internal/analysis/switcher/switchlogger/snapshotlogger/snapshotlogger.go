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
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/logger"
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

type SwitchType string

const (
	SwitchTypePre  SwitchType = "pre-switch"
	SwitchTypePost SwitchType = "post-switch"
)

// StdSwitchingSnapshotData is the data structure for switching snapshot logging to standard output.
type StdSwitchingSnapshotData struct {
	DbType               string          `json:"db_type,omitempty"`
	ActionScope          string          `json:"action_scope,omitempty"`
	StrategyJSON         json.RawMessage `json:"strategy,omitempty"`
	FailureInstancesJSON json.RawMessage `json:"failure_instances,omitempty"`
	MetadataSetJSON      json.RawMessage `json:"metadata_set,omitempty"`
}

// DbSwitchingSnapshotData is the data structure for switching snapshot logging to DB.
type DbSwitchingSnapshotData struct {
	StartTime    *time.Time `json:"start_time,omitempty"`
	FinishedTime *time.Time `json:"finished_time,omitempty"`
	SwitchID     string     `json:"switch_id,omitempty"`
	BkBizID      int        `json:"bk_biz_id,omitempty"`
	BkCloudID    int        `json:"bk_cloud_id,omitempty"`
	ClusterID    int        `json:"cluster_id,omitempty"`
	ClusterName  string     `json:"cluster_name,omitempty"`
	Reason       string     `json:"reason,omitempty"`
	Result       string     `json:"result,omitempty"`
}

// SwitchingSnapshotData is the data structure for switching snapshot logging.
type SwitchingSnapshotData struct {
	DbSwitchingSnapshotData
	StdSwitchingSnapshotData

	MetadataSet      []*dbm.DbInstMetadata `json:"-"`
	SwSnapshotLogger logger.Logger         `json:"-"`
}

// SwitchingSnapshotReport is the data structure for switching snapshot reporting.
type SwitchingSnapshotReport struct {
	SnapshotData    *SwitchingSnapshotData
	SnapshotLoggers []SnapshotLogger
}

// NewSwitchingSnapshotReport creates a new SwitchingSnapshotReport instance.
func NewSwitchingSnapshotReport(snapshotData *SwitchingSnapshotData, startTime time.Time) *SwitchingSnapshotReport {
	if snapshotData == nil {
		return &SwitchingSnapshotReport{}
	}
	snapshotData.StartTime = &startTime

	snapshotLoggers := []SnapshotLogger{}

	dbSnapshotHdl, dbSnapshotErr := NewDbSnapshotHandlerFromConfig()
	if dbSnapshotErr != nil {
		logger.Warn("failed to create db snapshot handler, switchId: %s, errmsg: %s", snapshotData.SwitchID, dbSnapshotErr)
	} else {
		if openErr := dbSnapshotHdl.Open(); openErr != nil {
			logger.Warn("failed to open db snapshot handler, switchId: %s, errmsg: %s", snapshotData.SwitchID, openErr)
		} else {
			snapshotLoggers = append(snapshotLoggers, dbSnapshotHdl)
		}
	}

	swSnapshotLogger := NewStdSnapshotHandler(snapshotData.SwSnapshotLogger)
	snapshotLoggers = append(snapshotLoggers, swSnapshotLogger)

	return &SwitchingSnapshotReport{
		SnapshotData:    snapshotData,
		SnapshotLoggers: snapshotLoggers,
	}
}

// ReportBeforeSwitchingSnapshot reports the switching snapshot before switching.
func (s *SwitchingSnapshotReport) ReportBeforeSwitchingSnapshot() {
	if s.SnapshotData == nil {
		return
	}

	for _, l := range s.SnapshotLoggers {
		if appendErr := l.PreSwitchLog(s.SnapshotData); appendErr != nil {
			logger.Warn("failed to create switching snapshot record, switchId: %s, errmsg: %s",
				s.SnapshotData.SwitchID, appendErr)
		}
	}
}

// ReportAfterSwitchingSnapshot reports the switching snapshot after switching.
func (s *SwitchingSnapshotReport) ReportAfterSwitchingSnapshot(rspErr error) {
	if s.SnapshotData == nil {
		return
	}

	now := time.Now()
	s.SnapshotData.FinishedTime = &now
	if rspErr != nil {
		s.SnapshotData.Result = fmt.Sprintf("switching failed: %s", rspErr.Error())
	} else {
		s.SnapshotData.Result = "switching completed successfully"
	}

	for _, l := range s.SnapshotLoggers {
		if appendErr := l.PostSwitchLog(s.SnapshotData); appendErr != nil {
			logger.Warn("failed to create switching snapshot record, switchId: %s, errmsg: %s",
				s.SnapshotData.SwitchID, appendErr)
		}
	}
}
