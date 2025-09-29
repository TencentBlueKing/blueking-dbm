package mongodb_rpc

import (
	"fmt"
	"log/slog"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

// QueryResp 查询结果
// code: 0 成功，1 失败
// data: 查询结果
// error_msg: 错误信息 （当code为1时）
type QueryResp struct {
	Code            int    `json:"code"`
	Data            string `json:"data"`              // 查询结果
	ErrorMsg        string `json:"error_msg"`         // 错误信息
	DebugInfo       string `json:"debug_info"`        // session信息
	SessionReqCount int    `json:"session_req_count"` // 请求次数
}

type respHandle struct {
	c      *gin.Context
	param  *QueryParams
	logger *slog.Logger
}

func (r *respHandle) SendResp(data string, code int, errMsg string, sessionReqCount int) {
	if r.logger == nil {
		panic("logger is nil")
	}

	debugInfo := ""
	if r.param != nil {
		debugInfo = r.param.GetUniqSessionToken()
	} else {
		debugInfo = "-"
	}

	r.logger.Info("sendmsg",
		slog.String("data", shortMsg(data, 512)),
		slog.Int("code", code),
		slog.String("errMsg", errMsg),
		slog.String("debugInfo", debugInfo),
		slog.Int("sessionReqCount", sessionReqCount),
	)
	r.c.JSON(http.StatusOK, QueryResp{
		Code:            code,
		ErrorMsg:        errMsg,
		Data:            data,
		DebugInfo:       debugInfo,
		SessionReqCount: sessionReqCount,
	})
}

// SendError send a resp with code 1
func (r *respHandle) SendError(errMsg string, sessionReqCount int) {
	r.SendResp(fmt.Sprintf("disconnect. error: %s", errMsg), 0, "", sessionReqCount)
}

func NewRespHandle(c *gin.Context, param *QueryParams, logger *slog.Logger) *respHandle {
	return &respHandle{
		c:      c,
		param:  param,
		logger: logger,
	}
}

// shortMsg 截取字符串，如果超过maxLen，则截取maxLen个字符，并添加...
func shortMsg(msg string, maxLen int) string {
	if maxLen <= 0 {
		maxLen = 512
	}
	if len(msg) > maxLen+30 {
		return msg[:maxLen/2] + " ... (len:" + strconv.Itoa(len(msg)) + ") ... " + msg[len(msg)-maxLen/2:]
	}
	return msg
}
