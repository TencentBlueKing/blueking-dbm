package common

import (
	"dbm-services/common/reverseapi/pkg/core"
	"encoding/json"
	"time"

	"dbm-services/common/reverseapi/define/common"

	"github.com/google/uuid"
	"github.com/pkg/errors"
)

type innerEvent struct {
	PayLoad     common.ISyncReportEvent `json:"payload"`
	BkBizId     int64                   `json:"bk_biz_id"`
	ClusterType string                  `json:"cluster_type"`
	EventType   string                  `json:"event_type"`
	// EventCreateTimestamp 毫秒
	EventCreateTimestamp int64 `json:"event_create_timestamp"`
	// EventReportTimestamp 毫秒
	EventReportTimestamp int64  `json:"event_report_timestamp"`
	EventUUID            string `json:"event_uuid"`
}

func (i *innerEvent) MarshalJSON() ([]byte, error) {
	payloadJson, err := json.Marshal(i.PayLoad)
	if err != nil {
		return nil, err
	}
	payloadMap := make(map[string]interface{})
	err = json.Unmarshal(payloadJson, &payloadMap)
	if err != nil {
		return nil, err
	}
	// 在 event 平级注入内置字段
	payloadMap["bk_biz_id"] = i.BkBizId
	payloadMap["cluster_type"] = i.ClusterType
	payloadMap["event_type"] = i.EventType
	payloadMap["event_create_timestamp"] = i.EventCreateTimestamp
	payloadMap["event_uuid"] = i.EventUUID
	payloadMap["event_report_timestamp"] = i.EventReportTimestamp
	return json.Marshal(payloadMap)
}

// SyncReport
// 这个接口的返回比较复杂一点
// err != nil && data == nil 时, 是普通的错误, 比如网络问题, django 挂了这类的
// err != nil && data != nil 时, 是反向 post 的协议错误, 比如 cluster type, event type 未注册啥的
func SyncReport[T common.ISyncReportEvent](core *core.Core, events ...T) ([]byte, error) {
	if core == nil {
		return nil, errors.New("SyncReport core is nil")
	}
	var innerEvents []innerEvent
	for _, e := range events {
		innerEvents = append(innerEvents, innerEvent{
			PayLoad:              e,
			BkBizId:              e.EventBkBizId(),
			ClusterType:          e.ClusterType(),
			EventType:            e.EventType(),
			EventCreateTimestamp: e.EventCreateTimeStamp(),
			EventReportTimestamp: time.Now().UnixMilli(),
			EventUUID:            uuid.New().String(),
		})
	}

	b, err := json.Marshal(innerEvents)
	if err != nil {
		return nil, errors.Wrapf(err, "failed to marshal events")
	}

	data, err := core.Post("common/sync_report/", b)
	if err != nil {
		if data != nil {
			reportErr := common.SyncReportError[T]{}
			err = json.Unmarshal(data, &reportErr)
			if err != nil {
				return nil, err
			}
			return nil, reportErr
		}
		return nil, errors.Wrapf(err, "failed to report events")
	}

	return data, nil
}
