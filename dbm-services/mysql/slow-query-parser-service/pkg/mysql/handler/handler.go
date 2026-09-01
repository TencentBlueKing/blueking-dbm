package handler

import (
	"log/slog"
	"net/http"
	"regexp"

	"github.com/gin-gonic/gin"

	"dbm-services/mysql/slow-query-parser-service/pkg/mysql"
)

var SqlTextReplace = regexp.MustCompile(`# Time: .*`)

// AddRouter TODO
func AddRouter(r *gin.Engine) {
	g := r.Group("/mysql")

	g.POST("/", func(ctx *gin.Context) {
		body := mysql.Request{}
		err := ctx.BindJSON(&body)
		if err != nil {
			slog.Error("mysql", err)
			ctx.JSON(http.StatusBadRequest, err.Error())
			return
		}
		sqlText := SqlTextReplace.ReplaceAllString(body.Content, "")
		res, err := mysql.AnalyzeSql(body.Db, sqlText)
		if err != nil {
			slog.Error("mysql", err)
			ctx.JSON(http.StatusInternalServerError, err.Error())
			return
		}

		ctx.JSON(http.StatusOK, res)
	})
}
