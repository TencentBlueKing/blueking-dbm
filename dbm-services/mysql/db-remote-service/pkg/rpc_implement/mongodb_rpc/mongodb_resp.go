package mongodb_rpc

import (
	"log/slog"
	"net/http"

	"github.com/gin-gonic/gin"
)

// QueryResp 查询结果
// code: 0 成功，1 失败
// data: 查询结果
// error_msg: 错误信息 （当code为1时）
type QueryResp struct {
	Code     int    `json:"code"`
	Data     string `json:"data"`      // 查询结果
	ErrorMsg string `json:"error_msg"` // 错误信息
}

type respHandle struct {
	c      *gin.Context
	param  *QueryParams
	logger *slog.Logger
}

func (r *respHandle) SendResp(data string, code int, errMsg string) {
	if r.logger == nil {
		panic("logger is nil")
	}
	r.logger.Info("sendmsg",
		slog.String("data", data),
		slog.Int("code", code),
		slog.String("errMsg", errMsg))

	r.c.JSON(http.StatusOK, QueryResp{
		Code:     code,
		ErrorMsg: errMsg,
		Data:     data,
	})
}

// SendError send a resp with code 1
func (r *respHandle) SendError(errMsg string) {
	r.SendResp("", 1, errMsg)
}

func NewRespHandle(c *gin.Context, param *QueryParams, logger *slog.Logger) *respHandle {
	return &respHandle{
		c:      c,
		param:  param,
		logger: logger,
	}
}
