package rpc

import (
	"log/slog"
	"net/http"
	"strings"
	"time"

	"dbm-services/mysql/db-remote-service/pkg/config"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

func Handler(c *gin.Context) {
	rid := requestid.Get(c)

	req, err := BuildRequestWithDefault(c)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	slog.Info("v2 proxy-admin rpc request",
		slog.String("request_id", rid),
		slog.String("addresses", strings.Join(req.Addresses, ",")),
		slog.String("cmds", strings.Join(req.Cmds, ",")),
		slog.Bool("force", req.Force),
	)

	start := time.Now()
	user := config.RuntimeConfig.ProxyAdminUser
	password := config.RuntimeConfig.ProxyAdminPassword

	res, err := req.execute(c.Request.Context(), user, password)
	elapsed := time.Since(start)

	if err != nil {
		slog.Error("v2 proxy-admin rpc finished with error",
			slog.String("request_id", rid),
			slog.Duration("elapsed", elapsed),
			slog.String("error", err.Error()),
			slog.Any("response", res),
		)
		c.JSON(
			http.StatusInternalServerError,
			gin.H{
				"code": 1,
				"data": res,
				"msg":  err.Error(),
			})
		return
	}

	slog.Info("v2 proxy-admin rpc finished",
		slog.String("request_id", rid),
		slog.Duration("elapsed", elapsed),
		slog.Any("response", res),
	)

	c.JSON(
		http.StatusOK,
		gin.H{
			"code": 0,
			"data": res,
			"msg":  "",
		})
}
