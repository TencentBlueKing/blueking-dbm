package api

import (
	"k8s-dbs/src/core/entity"

	"github.com/gin-gonic/gin"
)

const HealthCheckUrl = "/common/health"

func HealthCheck(ctx *gin.Context) {
	entity.SuccessResponse(ctx, nil, "OK")
}
