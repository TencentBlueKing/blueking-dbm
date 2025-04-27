package entity

import (
	"encoding/json"
	coreErrors "k8s-dbs/src/core/errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/pkg/errors"
)

type ResponseCode int

// Response the src response
type Response struct {
	Result    bool         `json:"result"`
	Code      ResponseCode `json:"code"`
	Data      interface{}  `json:"data"`
	Message   string       `json:"message"`
	RealError interface{}  `json:"error"`
}

// SuccessResponse response after successful request execution
func SuccessResponse(ctx *gin.Context, data interface{}, message string) {
	resp := &Response{
		Result:    true,
		Code:      http.StatusOK,
		Data:      data,
		Message:   message,
		RealError: nil,
	}
	ctx.JSON(http.StatusOK, resp)
	response, _ := json.Marshal(resp)
	ctx.Set("response", string(response))
}

// ErrorResponse response after failed request execution
func ErrorResponse(ctx *gin.Context, err error) {
	//判断错误类型
	// As - 获取错误的具体实现
	var code ResponseCode
	var myError = new(coreErrors.GlobalError)
	if errors.As(err, &myError) {
		code = ResponseCode(myError.Code)
	}
	resp := &Response{
		Result:    false,
		Code:      code,
		Data:      nil,
		Message:   err.Error(),
		RealError: myError.RealErrorMessage,
	}
	ctx.JSON(http.StatusOK, resp)
	response, _ := json.Marshal(resp)
	ctx.Set("response", string(response))
}
