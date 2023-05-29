// Package handler TODO
package handler

import (
	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/pkg/core/logger"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

// Response TODO
type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// Response2 TODO
type Response2 struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    string `json:"data"`
}

// SendResponse TODO
func SendResponse(ctx *gin.Context, err error, data interface{}) {
	code, message := errno.DecodeErr(err)
	req := fmt.Sprintf("url:%s params:%+v", ctx.Request.RequestURI, ctx.Params)
	data2, _ := json.Marshal(data)
	logger.Info("req:%s resp: %+v", req, Response2{
		Code:    code,
		Message: message,
		Data:    string(data2),
	})
	// always return http.StatusOK
	ctx.JSON(http.StatusOK, Response{
		Code:    code,
		Message: message,
		Data:    data,
	})
}
