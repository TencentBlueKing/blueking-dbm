package common

import (
	"encoding/json"
	"time"
)

type ISyncReportEvent interface {
	ClusterType() string
	EventType() string
	// EventCreateTime 会自动转成 UTC 时间的微秒上报
	EventCreateTime() time.Time
	EventBkBizId() int64
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
