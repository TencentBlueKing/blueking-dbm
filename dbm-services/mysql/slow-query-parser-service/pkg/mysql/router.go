package mysql

import (
	"log/slog"
	"net/http"
	"regexp"

	"github.com/gin-gonic/gin"
)

var SqlTextReplace = regexp.MustCompile(`# Time: .*`)

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
		// slog.Info("mysql", slog.Any("body", body), slog.String("path", g.BasePath()))
		sqlText := SqlTextReplace.ReplaceAllString(body.Content, "")
		res, err := AnalyzeSql(body.Db, sqlText)
		if err != nil {
			slog.Error("mysql", err)
			ctx.JSON(http.StatusInternalServerError, err.Error())
			return
		}

		ctx.JSON(http.StatusOK, res)
	})
}
