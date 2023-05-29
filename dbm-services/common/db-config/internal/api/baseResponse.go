package api

import (
	"encoding/json"
)

// BaseApiResponse TODO
type BaseApiResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// BaseApiRespInterface TODO
type BaseApiRespInterface struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// HTTPOkNilResp TODO
type HTTPOkNilResp struct {
	Code    int         `json:"code" example:"200"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// HTTPClientErrResp TODO
type HTTPClientErrResp struct {
	Code    int         `json:"code" example:"400"`
	Message string      `json:"message" example:"输入参数错误"` // status bad request
	Data    interface{} `json:"data"`
}

// HTTPServerErrResp TODO
type HTTPServerErrResp struct {
	Code    int         `json:"code" example:"500"`
	Message string      `json:"message" example:"服务端错误"` // server internal error
	Data    interface{} `json:"data"`
}
