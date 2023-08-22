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

			//for _, hs := range Handlers {
			//	for _, h := range hs {
			//		logger.Debug("handler", slog.String(
			//			"addr",
			//			fmt.Sprintf("%x",
			//				reflect.ValueOf(h.Worker).Pointer())))
			//	}
			//}

			for _, r := range engine.Routes() {
				routes = append(routes, &rt{Method: r.Method, Path: r.Path})
				//logger.Debug("routes info", slog.Any("handle func", r.HandlerFunc), slog.Any("handler", r.Handler))
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
