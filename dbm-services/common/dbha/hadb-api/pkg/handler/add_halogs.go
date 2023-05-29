package handler

import (
	"dbm-services/common/dbha/hadb-api/pkg/handler/halogs"
)

func init() {
	AddToApiManager(ApiHandler{
		Url:     "/halogs/",
		Handler: halogs.Handler,
	})
}
