// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package configreport

import (
	"log/slog"
	"os"
	"path/filepath"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/reportlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
)

// DynamicEvent 事件
// 结构化内容: {"event_name":"xxxx", "payload":object}
type DynamicEvent struct {
	EventName string      `json:"event_name"`
	Payload   interface{} `json:"payload"`

	clusterType string
	bkBizId     int64
}

func (e *DynamicEvent) ClusterType() string {
	return e.clusterType
}
func (e *DynamicEvent) EventType() string {
	return e.EventName
}
func (e *DynamicEvent) EventCreateTimeStamp() int64 {
	return time.Now().UnixMicro()
}
func (e *DynamicEvent) EventBkBizId() int64 {
	return e.bkBizId
}

/*
	func (e *DynamicEvent) MarshalJSON() ([]byte, error) {
		if e.Payload == nil {
			return nil, errors.New("payload is nil")
		}
		return json.Marshal(e.Payload)
	}
*/
func (e *DynamicEvent) SetPayload(v interface{}) {
	e.Payload = v
}

func NewDynamicEvent(eventName, clusterType string, bkBizId int64) *DynamicEvent {
	return &DynamicEvent{
		EventName:   eventName,
		clusterType: clusterType,
		bkBizId:     bkBizId,
	}
}

// GetMixedReport 上报写到目录下 mixed/xxx
func GetMixedReport(reportFile string) (*reportlog.Reporter, error) {
	mixedReportBaseDir := filepath.Join(cst.DBAReportBase, "mixed")
	err := os.MkdirAll(mixedReportBaseDir, os.ModePerm)
	if err != nil {
		slog.Error("failed to create report directory", slog.String("error", err.Error()))
		return nil, errors.Wrap(err, "failed to create report directory")
	}
	return reportlog.NewReporter(mixedReportBaseDir, reportFile, nil)
}
