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

// ReadHandler Oracle 只读查询 (账号来自 ORACLE_SYS_READ_USER / ORACLE_SYS_READ_PASSWORD)
var ReadHandler = makeHandler("oracle/rpc",
	func() (string, string) {
		return config.RuntimeConfig.OracleSysReadUser, config.RuntimeConfig.OracleSysReadPassword
	},
)

func makeHandler(endpoint string, account func() (user, password string)) gin.HandlerFunc {
	return func(c *gin.Context) {
		rid := requestid.Get(c)

		req, err := BuildRequestWithDefault(c)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		user, password := account()
		if user == "" || password == "" {
			c.JSON(http.StatusInternalServerError, gin.H{
				"code": 1,
				"data": nil,
				"msg":  "oracle read account is not configured (ORACLE_SYS_READ_USER / ORACLE_SYS_READ_PASSWORD)",
			})
			return
		}

		slog.Info("v2 oracle rpc request",
			slog.String("request_id", rid),
			slog.String("endpoint", endpoint),
			slog.String("addresses", strings.Join(req.Addresses, ",")),
			slog.String("service_name", req.ServiceName),
			slog.Int("cmd_count", len(req.Cmds)),
			slog.Bool("force", req.Force),
		)

		start := time.Now()
		res, err := req.execute(c.Request.Context(), user, password)
		elapsed := time.Since(start)

		// 查询结果可能大，日志只记录每个地址的错误信息, 不打印 table_data
		addrErrors := make([]string, 0)
		for _, r := range res {
			if r.Error != "" {
				addrErrors = append(addrErrors, r.Address+": "+r.Error)
			}
		}

		if err != nil {
			slog.Error("v2 oracle rpc finished with error",
				slog.String("request_id", rid),
				slog.String("endpoint", endpoint),
				slog.Duration("elapsed", elapsed),
				slog.String("error", err.Error()),
				slog.Any("address_errors", addrErrors),
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

		slog.Info("v2 oracle rpc finished",
			slog.String("request_id", rid),
			slog.String("endpoint", endpoint),
			slog.Duration("elapsed", elapsed),
			slog.Any("address_errors", addrErrors),
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
