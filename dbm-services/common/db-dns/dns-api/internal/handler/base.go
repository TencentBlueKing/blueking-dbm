package handler

import (
	"bk-dnsapi/pkg/errno"
	"bk-dnsapi/pkg/logger"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Handler struct {
}

// Routes 接口路由
func (h *Handler) Routes() []*gin.RouteInfo {
	return []*gin.RouteInfo{
		{Method: http.MethodPut, Path: "/domain", HandlerFunc: h.AddDns},

		{Method: http.MethodDelete, Path: "/domain", HandlerFunc: h.DelDns},

		{Method: http.MethodPost, Path: "/domain", HandlerFunc: h.UpdateDns},
		{Method: http.MethodPost, Path: "/domain/batch", HandlerFunc: h.UpdateBatchDns},
		{Method: http.MethodPost, Path: "/config", HandlerFunc: h.UpdateConfig},
		{Method: http.MethodPost, Path: "/domain/app", HandlerFunc: h.UpdateDomainApp},

		{Method: http.MethodGet, Path: "/domain", HandlerFunc: h.GetDns},
		{Method: http.MethodGet, Path: "/domain/all", HandlerFunc: h.GetAllDns},
		{Method: http.MethodGet, Path: "/config/all", HandlerFunc: h.GetAllConfig},
	}
}

// Response 响应结构体
type Response struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    Data   `json:"data"`
}

// Data Data结构体
type Data struct {
	Detail  interface{} `json:"detail"`
	RowsNum int64       `json:"rowsNum"`
}

// SendResponse 发送响应
func SendResponse(c *gin.Context, err error, data Data) {
	code, message := errno.DecodeErr(err)
	logger.Info(fmt.Sprintf("send response: {code:%d, message:%s, rowsnum:%d}", code, message, data.RowsNum))
	c.JSON(http.StatusOK, Response{
		Code:    code,
		Message: message,
		Data:    data,
	})
}
