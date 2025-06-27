package common

import (
	"encoding/json"
	"time"
)

type ISyncReportEvent interface {
	ClusterType() string
	EventType() string
	EventCreateTimeStamp() time.Time
	BkBizId() int64
	// MarshalJSON 上报的 json 主体
	MarshalJSON() ([]byte, error)
}

type SyncReportErrDetail[T ISyncReportEvent] struct {
	Event  T      `json:"event"`
	Reason string `json:"reason"`
}

func (f SyncReportErrDetail[T]) String() string {
	b, _ := json.Marshal(f)
	return string(b)
}

type SyncReportError[T ISyncReportEvent] []SyncReportErrDetail[T]

func (s SyncReportError[T]) Error() string {
	return "demo error"
}

func (s SyncReportError[T]) ErrDetail() []SyncReportErrDetail[T] {
	return s
}
