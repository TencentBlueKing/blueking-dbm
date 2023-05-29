package handler

import (
	"dbm-services/common/dbha/hadb-api/pkg/handler/dbstatus"
)

func init() {
	AddToApiManager(ApiHandler{
		Url:     "/dbstatus/",
		Handler: dbstatus.Handler,
	})
}
