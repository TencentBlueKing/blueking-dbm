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

package failure

import (
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Instance represents one instance that detector marked as failure (needs switching).
type Instance struct {
	BkCloudID       int                             `json:"bk_cloud_id"`
	IP              string                          `json:"ip"`
	Port            int                             `json:"port"`
	BkBizID         int                             `json:"bk_biz_id"`
	Cluster         string                          `json:"cluster"`
	ClusterID       int                             `json:"cluster_id"`
	DbType          haprobe.DbType                  `json:"db_type"`
	EventName       haprobe.DbEventName             `json:"event_name"`
	EventNameReason haprobe.DbEventNameReason       `json:"event_name_reason"`
	ClusterType     haprobe.DbmMetadataClusterType  `json:"cluster_type"`
	MachineType     haprobe.DbmMetadataMachineType  `json:"machine_type"`
	InstanceRole    haprobe.DbmMetadataInstanceRole `json:"instance_role"`

	// CheckStartTime and CheckFinishedTime are the start and end times of the instance's
	// SSH double-check detection.
	CheckStartTime    *time.Time `json:"check_start_time,omitempty"`
	CheckFinishedTime *time.Time `json:"check_finished_time,omitempty"`
}
