package handler

import "dbm-services/common/dbha/hadb-api/pkg/handler/switchlog"

func init() {
	AddToApiManager(ApiHandler{
		Url:     "/switchlogs/",
		Handler: switchlog.Handler,
	})
}
