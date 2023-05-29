// Package api TODO
package api

import (
	"encoding/json"

	"github.com/valyala/fasthttp"
)

const (
	// RespOK TODO
	RespOK = 0
	// RespErr TODO
	RespErr = 1
)

const (
	// RowsAffect TODO
	RowsAffect = "rowsAffected"
)

// QueryPage TODO
type QueryPage struct {
	Limit  int `json:"limit"`
	Offset int `json:"offset"`
}

// RequestInfo TODO
type RequestInfo struct {
	// bk_cloud_id is needed by proxypass
	BkCloudId int `json:"bk_cloud_id"`
	// bk_token is needed by proxypass
	BkToken string `json:"bk_token"`
	// api name
	Name string `json:"name"`
	// query args from request.body
	QueryArgs interface{} `json:"query_args"`
	// set args from request.body
	SetArgs interface{} `json:"set_args"`
	// query limit
	PageArgs QueryPage `json:"page_args"`
}

// ResponseInfo TODO
type ResponseInfo struct {
	Code    int         `json:"code"`
	Message string      `json:"msg"`
	Data    interface{} `json:"data"`
}

// SendResponse TODO
func SendResponse(ctx *fasthttp.RequestCtx, responseInfo ResponseInfo) {
	body, err := json.Marshal(responseInfo)
	if err != nil {
		responseInfo.Data = ""
		responseInfo.Message = err.Error()
		responseInfo.Code = 1
	}
	ctx.Response.SetBody(body)
	ctx.Response.Header.SetContentType("application/json")
	ctx.Response.SetStatusCode(fasthttp.StatusOK)
}
