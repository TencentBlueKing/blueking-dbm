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

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// SwitchSnapshotPayload is logged as JSON after SwitchID in switching-snapshot-* log files.
type SwitchSnapshotPayload struct {
	DbType           string          `json:"db_type"`
	ActionScope      string          `json:"action_scope"`
	Strategy         json.RawMessage `json:"strategy"`
	FailureInstances json.RawMessage `json:"failure_instances"`
	MetadataSet      json.RawMessage `json:"metadata_set"`
}

// WriteSwitchSnapshot writes one line: SwitchID, then JSON SwitchSnapshotPayload.
// swSnapshotLogger is the dedicated rotating file logger; nil disables writing.
// strategy / group may be nil (encoded as JSON null / empty arrays in sub-documents).
func WriteSwitchSnapshot(
	strategy *hamodel.DbSwitchingStrategy,
	group *FailureGroup,
	req *switcher.Request,
	swSnapshotLogger logger.Logger,
) {
	if swSnapshotLogger == nil {
		return
	}

	if req == nil {
		swSnapshotLogger.Warn("skip saving switching snapshot: switch request is nil")
		return
	}

	strategyJSON, err := json.Marshal(strategy)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal strategy for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
		return
	}

	failures := []FailureInstanceInfo{}
	if group != nil && group.Instances != nil {
		failures = group.Instances
	}

	failureJSON, err := json.Marshal(failures)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal failure instances for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
		return
	}

	metaSet := []*dbm.DbInstMetadata{}
	if req.MySqlInstData != nil {
		metaSet = req.MySqlInstData
	}

	metadataJSON, err := json.Marshal(metaSet)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal metadata set for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
		return
	}

	payload := SwitchSnapshotPayload{
		DbType:           string(req.DbType),
		ActionScope:      string(req.ActionScope),
		Strategy:         strategyJSON,
		FailureInstances: failureJSON,
		MetadataSet:      metadataJSON,
	}

	body, err := json.Marshal(&payload)
	if err != nil {
		swSnapshotLogger.Warn("failed to marshal switching snapshot payload, switchId: %s, errmsg: %s", req.SwitchID, err)
		return
	}

	swSnapshotLogger.Info("%s\t%s", req.SwitchID, string(body))
}
