package rpc

import (
	"log/slog"
	"net/http"
	"strings"
	"time"

	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/sqlserver/internal/impl"

	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

// AdminHandler SQLServer admin 全权限, 对应 v1 /sqlserver/rpc
var AdminHandler = makeHandler("sqlserver/rpc",
	func() (string, string) {
		return config.RuntimeConfig.SqlserverAdminUser, config.RuntimeConfig.SqlserverAdminPassword
	},
	impl.AdminCommands,
)

// DataReadHandler SQLServer 业务数据只读, 对应 v1 /sqlserver/data-read-rpc
var DataReadHandler = makeHandler("sqlserver/data-read-rpc",
	func() (string, string) {
		return config.RuntimeConfig.SqlserverDataReadUser, config.RuntimeConfig.SqlserverDataReadPassword
	},
	impl.ReadOnlyCommands,
)

// SySReadHandler SQLServer 系统库只读, 对应 v1 /sqlserver/sys-read-rpc
var SySReadHandler = makeHandler("sqlserver/sys-read-rpc",
	func() (string, string) {
		return config.RuntimeConfig.SqlserverSySReadUser, config.RuntimeConfig.SqlserverSySReadPassword
	},
	impl.ReadOnlyCommands,
)

func makeHandler(endpoint string, account func() (user, password string), classifier *impl.CommandClassifier) gin.HandlerFunc {
	return func(c *gin.Context) {
		rid := requestid.Get(c)

		req, err := BuildRequestWithDefault(c, classifier)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		slog.Info("v2 sqlserver rpc request",
			slog.String("request_id", rid),
			slog.String("endpoint", endpoint),
			slog.String("addresses", strings.Join(req.Addresses, ",")),
			slog.String("cmds", strings.Join(req.Cmds, ",")),
			slog.Bool("force", req.Force),
		)

		start := time.Now()
		user, password := account()
		res, err := req.execute(c.Request.Context(), user, password)
		elapsed := time.Since(start)

		if err != nil {
			slog.Error("v2 sqlserver rpc finished with error",
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

		slog.Info("v2 sqlserver rpc finished",
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
