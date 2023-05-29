package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type rt struct {
	Method string `json:"method"`
	Path   string `json:"path"`
}

func HandleList(engine *gin.Engine) {
	engine.GET("list",
		func(ctx *gin.Context) {
			var routes []*rt

			for _, r := range engine.Routes() {
				routes = append(routes, &rt{Method: r.Method, Path: r.Path})
			}

			ctx.JSON(
				http.StatusOK,
				gin.H{
					"code": 0,
					"data": routes,
					"msg":  "",
				})
			return
		})
}
