package service

import "github.com/gin-gonic/gin"

var r *gin.Engine

func Init() {
	r = gin.Default()
	buildRouter(r)
}
