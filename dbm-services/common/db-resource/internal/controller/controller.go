// Package controller TODO
package controller

import (
	"fmt"
	"net/http"

	"dbm-services/common/db-resource/pkg/errno"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
)

// BaseHandler TODO
type BaseHandler struct{}

// Response TODO
type Response struct {
	Code      int         `json:"code"`
	Message   string      `json:"message"`
	Data      interface{} `json:"data"`
	RequestId string      `json:"request_id"`
}

// Prepare TODO
func (c *BaseHandler) Prepare(r *gin.Context, schema interface{}) error {
	requestId := r.GetString("request_id")
	if cmutil.IsEmpty(requestId) {
		err := fmt.Errorf("get request id error ~")
		c.SendResponse(r, err, nil, requestId)
		return err
	}
	if err := r.ShouldBind(&schema); err != nil {
		logger.Error("ShouldBind Failed %s", err.Error())
		c.SendResponse(r, err, nil, requestId)
		return err
	}
	logger.Info("param is %v", schema)
	return nil
}

// SendResponse TODO
// SendResponseT TODO
func (c *BaseHandler) SendResponse(r *gin.Context, err error, data interface{}, requestId string) {
	code, message := errno.DecodeErr(err)
	r.JSON(http.StatusOK, Response{
		Code:      code,
		Message:   message,
		Data:      data,
		RequestId: requestId,
	})
}
