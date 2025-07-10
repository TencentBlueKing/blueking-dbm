package common

import (
	"encoding/json"
)

type ISyncReportEvent interface {
	ClusterType() string
	EventType() string
	// EventCreateTimeStamp 微妙
	EventCreateTimeStamp() int64
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
