package handler

import (
	"dbm-services/common/dbha/hadb-api/pkg/handler/hastatus"
)

func init() {
	AddToApiManager(ApiHandler{
		Url:     "/hastatus/",
		Handler: hastatus.Handler,
	})
}
