package mysql

import (
	"log/slog"
	"net/http"

	"github.com/gin-gonic/gin"
)

// AddRouter TODO
func AddRouter(r *gin.Engine) {
	g := r.Group("/mysql")

	g.POST("/", func(ctx *gin.Context) {
		body := Request{}
		err := ctx.BindJSON(&body)
		if err != nil {
			slog.Error("mysql", err)
			ctx.JSON(http.StatusBadRequest, err.Error())
			return
		}

		slog.Info("mysql", slog.Any("body", body), slog.String("path", g.BasePath()))

		res, err := parse(body.Content)
		if err != nil {
			slog.Error("mysql", err)
			ctx.JSON(http.StatusInternalServerError, err.Error())
			return
		}

		ctx.JSON(http.StatusOK, res)
	})
}
