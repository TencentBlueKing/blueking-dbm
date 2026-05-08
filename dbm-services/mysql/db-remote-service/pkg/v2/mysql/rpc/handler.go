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

// AdminHandler 用 mysql admin 账号执行, 对应 v1 /mysql/rpc
var AdminHandler = makeHandler("mysql/rpc", func() (string, string) {
	return config.RuntimeConfig.MySQLAdminUser, config.RuntimeConfig.MySQLAdminPassword
})

// WebConsoleHandler 用 webconsole 只读账号执行, 对应 v1 /webconsole/rpc
var WebConsoleHandler = makeHandler("webconsole/rpc", func() (string, string) {
	return config.RuntimeConfig.WebConsoleUser, config.RuntimeConfig.WebConsolePassword
})

// makeHandler 按账号源生成 gin handler。
// 账号身份由 endpoint 决定, client 无法在请求体里指定, 防越权。
func makeHandler(endpoint string, account func() (user, password string)) gin.HandlerFunc {
	return func(c *gin.Context) {
		rid := requestid.Get(c)
		req, err := BuildRequestWithDefault(c)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		slog.Info("v2 rpc request",
			slog.String("request_id", rid),
			slog.String("endpoint", endpoint),
			slog.String("addresses", strings.Join(req.Addresses, ",")),
			slog.String("cmds", strings.Join(req.Cmds, ",")),
			slog.Bool("force", req.Force),
			slog.String("pre_hook_cmds", strings.Join(req.PreHookCmds, ",")),
			slog.Bool("skip_set_names", req.SkipSetNames),
		)

		start := time.Now()
		user, password := account()
		res, err := req.execute(c.Request.Context(), user, password)
		elapsed := time.Since(start)

		if err != nil {
			slog.Error("v2 rpc finished with error",
				slog.String("request_id", rid),
				slog.String("endpoint", endpoint),
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

		slog.Info("v2 rpc finished",
			slog.String("request_id", rid),
			slog.String("endpoint", endpoint),
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
}
