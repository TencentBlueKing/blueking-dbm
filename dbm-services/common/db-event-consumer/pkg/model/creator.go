package model

import (
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

// CustomCreator 1. 定义接口（用于编译时检查，非必须但推荐）
type CustomCreator interface {
	Create(objs interface{}, w sinker.DSWriter) error
}

type CustomMigrator interface {
	MigrateSchema(w sinker.DSWriter) error
}
