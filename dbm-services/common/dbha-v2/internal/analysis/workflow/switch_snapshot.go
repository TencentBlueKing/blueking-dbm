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
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger/snapshotlogger"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// NewSwitchingSnapshotData creates a new SwitchingSnapshotData instance.
func NewSwitchingSnapshotData(
	strategy *hamodel.DbSwitchingStrategy,
	group *FailureGroup,
	req *switcher.Request,
	swSnapshotLogger logger.Logger,
) *snapshotlogger.SwitchingSnapshotData {
	if strategy == nil || group == nil || req == nil || swSnapshotLogger == nil {
		return nil
	}

	data := &snapshotlogger.SwitchingSnapshotData{
		StdSwitchingSnapshotData: snapshotlogger.StdSwitchingSnapshotData{
			DbType:      string(req.DbType),
			ActionScope: string(req.ActionScope),
		},
		DbSwitchingSnapshotData: snapshotlogger.DbSwitchingSnapshotData{
			SwitchID:  req.SwitchID,
			BkCloudID: group.BkCloudID,
		},
		SwSnapshotLogger: swSnapshotLogger,
	}

	// marshal strategy
	strategyJSON, err := json.Marshal(strategy)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal strategy for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.StrategyJSON = strategyJSON
	}

	// marshal failure instances
	failures := []FailureInstanceInfo{}
	if group.Instances != nil {
		failures = group.Instances
	}

	failureJSON, err := json.Marshal(failures)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal failure instances for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.FailureInstancesJSON = failureJSON

		if len(group.Instances) > 0 {
			data.DbSwitchingSnapshotData.BkBizID = group.Instances[0].BkBizID
			data.DbSwitchingSnapshotData.ClusterID = group.Instances[0].ClusterID
			data.DbSwitchingSnapshotData.ClusterName = group.Instances[0].Cluster
			data.DbSwitchingSnapshotData.Reason = group.Instances[0].EventNameReason.Str().String()
		}
	}

	// marshal metadata set
	metaSet := []*dbm.DbInstMetadata{}
	if req.MySqlInstData != nil {
		metaSet = req.MySqlInstData
	}
	data.MetadataSet = metaSet

	metadataJSON, err := json.Marshal(metaSet)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal metadata set for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.MetadataSetJSON = metadataJSON
	}

	return data
}
