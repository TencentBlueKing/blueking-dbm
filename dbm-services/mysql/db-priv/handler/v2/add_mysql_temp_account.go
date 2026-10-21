package v2

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/handler"
	"dbm-services/mysql/priv-service/service/v2/add_mysql_temp_account"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"

	"github.com/gin-gonic/gin"
)

func AddMySQLTempAccount(c *gin.Context) {
	slog.Info("AddMySQLTempAccount")

	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("ioutil.ReadAll", err)
		handler.SendResponse(c, errno.ErrBind, err)
		return
	}

	var input add_mysql_temp_account.Param
	if err := json.Unmarshal(body, &input); err != nil {
		slog.Error("json.Unmarshal", err)
		handler.SendResponse(c, errno.ErrBind, err)
		return
	}

	report, err := add_mysql_temp_account.AddMySQLTempAccount(&input)
	slog.Error("report", slog.Any("report", report), slog.Any("err", err))
	if report != nil || err != nil {
		rbody := gin.H{
			"code": 0,
			"msg":  "",
			"data": nil,
		}
		if report != nil {
			rbody["data"] = report
		}
		if err != nil {
			rbody["msg"] = err.Error()
		}
		c.JSON(
			http.StatusOK, rbody,
		)
	} else {
		c.JSON(http.StatusOK, gin.H{})
	}
	return
}
