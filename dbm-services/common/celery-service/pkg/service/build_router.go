package service

import (
	"github.com/gin-gonic/gin"

	"github.com/iancoleman/strcase"

	"celery-service/pkg/handler"
)

func buildRouter(engine *gin.Engine) {
	handler.InitHandlers()

	for dbType, hs := range handler.Handlers {
		g := engine.Group(strcase.ToKebab(dbType))
		for _, h := range hs {
			g.POST(strcase.ToKebab(h.Name()), h.Handler())
		}
	}
}
