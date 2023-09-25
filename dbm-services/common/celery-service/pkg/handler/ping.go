package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func HandlePing(engine *gin.Engine) {
	engine.GET("ping",
		func(ctx *gin.Context) {
			ctx.String(http.StatusOK, "pong")
			return
		})
}
