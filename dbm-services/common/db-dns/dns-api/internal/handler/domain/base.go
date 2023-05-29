package domain

import (
	"bk-dnsapi/pkg/errno"
	"net/http"

	"github.com/gin-gonic/gin"
)

// Handler TODO
type Handler struct {
}

// Routes TODO
func (h *Handler) Routes() []*gin.RouteInfo {
	return []*gin.RouteInfo{
		{Method: http.MethodPut, Path: "/", HandlerFunc: h.AddDns},

		{Method: http.MethodDelete, Path: "//", HandlerFunc: h.DelDns},

		{Method: http.MethodPost, Path: "/", HandlerFunc: h.UpdateDns},
		{Method: http.MethodPost, Path: "/batch", HandlerFunc: h.UpdateBatchDns},

		{Method: http.MethodGet, Path: "/", HandlerFunc: h.GetDns},
		{Method: http.MethodGet, Path: "/all", HandlerFunc: h.GetAllDns},
	}
}

// Response TODO
type Response struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    Data   `json:"data"`
}

// Data TODO
type Data struct {
	Detail  interface{} `json:"detail"`
	RowsNum int64       `json:"rowsNum"`
}

// SendResponse TODO
func SendResponse(c *gin.Context, err error, data Data) {
	code, message := errno.DecodeErr(err)

	c.JSON(http.StatusOK, Response{
		Code:    code,
		Message: message,
		Data:    data,
	})
}
