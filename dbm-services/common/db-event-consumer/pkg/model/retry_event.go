// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"log/slog"

	json "github.com/goccy/go-json"
	"github.com/pkg/errors"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

// DbmRetryEvent 用于消费客户端上报失败后通过 bklog 日志采集补报的事件
// 它不直接入库，而是根据 event_type 路由到对应的 model 消费入库逻辑
/* sample
{
  "payload": {
    "backup_id": "b3915c85-96b7-11f1-a390-1234567890",
    "backup_type": "logical",
    "cluster_id": 123,
    "cluster_address": "testdb.domain.db",
    "backup_host": "1.2.3.4",
    "backup_port": 3306,
    "mysql_role": "slave",
    "shard_value": 0,
    "bill_id": "",
    "bk_biz_id": 123,
    "mysql_version": "8.0.32",
    "data_schema_grant": "all",
    "is_full_backup": true,
    "backup_consistent_time": "2026-08-13T09:41:54+08:00",
    "backup_begin_time": "2026-08-13T09:41:54+08:00",
    "backup_end_time": "2026-08-13T09:42:25+08:00",
    "consistent_backup_time": "2026-08-13T09:41:54+08:00",
    "backup_method": "full_by_regular",
    "is_standby": "yes",
    "bk_cloud_id": 0,
    "file_retention_tag": "MYSQL_FULL_BACKUP",
    "total_filesize": 89020567
  },
  "bk_biz_id": 1234,
  "cluster_type": "tendbha",
  "event_type": "mysql_dbbackup_result",
  "event_create_timestamp": 1786585314000000,
  "event_report_timestamp": 1786585479863912,
  "event_uuid": "506c0448-965e-45a0-a0be-134567890"
}
*/
type DbmRetryEvent struct {
	Payload              json.RawMessage `json:"payload"`
	BkBizId              int             `json:"bk_biz_id"`
	ClusterType          string          `json:"cluster_type"`
	EventType            string          `json:"event_type"`
	EventCreateTimestamp int64           `json:"event_create_timestamp"`
	EventReportTimestamp int64           `json:"event_report_timestamp"`
	EventUuid            string          `json:"event_uuid"`
}

func (m *DbmRetryEvent) TableName() string {
	return "dbm_retry_event"
}

func (m *DbmRetryEvent) StrictSchema() bool {
	return true
}

// MigrateSchema retry event 本身不需要建表，它路由到其他 model 入库
func (m *DbmRetryEvent) MigrateSchema(w base.DSWriter) error {
	slog.Info("skip migrate for DbmRetryEvent, it routes to other models")
	return nil
}

// Create 根据 event_type 路由到对应 model 的 AnySinker，复用完整的消费入库逻辑
func (m *DbmRetryEvent) Create(objs interface{}, w base.DSWriter) error {
	retryEvents, ok := objs.([]DbmRetryEvent)
	if !ok {
		retryEvents = []DbmRetryEvent{objs.(DbmRetryEvent)}
	}

	// 按 event_type 分组，每组收集注入公共字段后的 payload
	grouped := make(map[string][][]byte)
	for _, event := range retryEvents {
		if event.EventType == "" {
			slog.Warn("retry event has empty event_type, skip", slog.String("event_uuid", event.EventUuid))
			continue
		}
		payload, err := m.injectBaseFields(event)
		if err != nil {
			slog.Error("inject base fields to payload failed",
				slog.Any("error", err), slog.String("event_uuid", event.EventUuid))
			continue
		}
		grouped[event.EventType] = append(grouped[event.EventType], payload)
	}

	// 按 event_type(=topic name) 路由到对应的 AnySinker 处理，复用完整的消费入库链路
	var errs []error
	for eventType, payloads := range grouped {
		entry, exists := sinker.ModelDSWriterMap[eventType]
		if !exists || entry.Handler == nil {
			slog.Error("no registered handler for event_type, skip",
				slog.String("event_type", eventType), slog.Int("count", len(payloads)))
			errs = append(errs, errors.Errorf("no registered handler for event_type: %s", eventType))
			continue
		}

		if err := entry.Handler.HandleRawMessages(payloads); err != nil {
			slog.Error("route retry event to handler failed",
				slog.Any("error", err),
				slog.String("event_type", eventType),
				slog.Int("count", len(payloads)))
			errs = append(errs, err)
		} else {
			slog.Info("route retry event to handler success",
				slog.String("event_type", eventType),
				slog.Int("count", len(payloads)))
		}
	}

	if len(errs) > 0 {
		return errors.Errorf("retry event route errors: %v", errs)
	}
	return nil
}

// injectBaseFields 将外层的公共字段注入到 payload 中
func (m *DbmRetryEvent) injectBaseFields(event DbmRetryEvent) ([]byte, error) {
	var payloadMap map[string]interface{}
	if err := json.Unmarshal(event.Payload, &payloadMap); err != nil {
		return nil, errors.WithMessage(err, "unmarshal payload")
	}

	// 注入外层公共字段到 payload（如果 payload 中没有的话）
	if _, ok := payloadMap["event_create_timestamp"]; !ok {
		payloadMap["event_create_timestamp"] = event.EventCreateTimestamp
	}
	if _, ok := payloadMap["event_report_timestamp"]; !ok {
		payloadMap["event_report_timestamp"] = event.EventReportTimestamp
	}
	if _, ok := payloadMap["event_uuid"]; !ok {
		payloadMap["event_uuid"] = event.EventUuid
	}

	result, err := json.Marshal(payloadMap)
	if err != nil {
		return nil, errors.WithMessage(err, "marshal payload with base fields")
	}
	return result, nil
}
