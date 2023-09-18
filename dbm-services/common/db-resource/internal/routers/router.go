package routers

import (
	"dbm-services/common/db-resource/internal/controller/apply"
	"dbm-services/common/db-resource/internal/controller/manage"

	"github.com/gin-gonic/gin"
)

// RegisterRoutes TODO
func RegisterRoutes(engine *gin.Engine) {
	// 注册路由
	apply := apply.ApplyHandler{}
	apply.RegisterRouter(engine)
	// 机器资源管理
	manage := manage.MachineResourceHandler{}
	manage.RegisterRouter(engine)
}
