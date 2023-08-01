package handler

import (
	"github.com/gin-gonic/gin"

	"celery-service/pkg/config"
)

type IHandler interface {
	ClusterType() string
	Name() string
	Handler() gin.HandlerFunc
}

var Handlers = make(map[string][]IHandler)

func InitHandlers() {
	for _, et := range config.ExternalTasks {
		addExternalHandler(et)
	}
}
