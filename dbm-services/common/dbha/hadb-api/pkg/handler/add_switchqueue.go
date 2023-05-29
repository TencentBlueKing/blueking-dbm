package handler

import (
	"dbm-services/common/dbha/hadb-api/pkg/handler/switchqueue"
)

func init() {
	AddToApiManager(ApiHandler{
		Url:     "/switchqueue/",
		Handler: switchqueue.Handler,
	})
}
