package halogs

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/pkg/api"

	"github.com/valyala/fasthttp"
)

const (
	// PutLogs TODO
	PutLogs = "reporter_log"
)

// Handler TODO
func Handler(ctx *fasthttp.RequestCtx) {
	param := &api.RequestInfo{}
	if err := json.Unmarshal(ctx.PostBody(), param); err != nil {
		log.Logger.Errorf("parse request body failed:%s", err.Error())
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: err.Error(),
		})
		return
	}
	switch param.Name {
	case PutLogs:
		PutHALogs(ctx, param.SetArgs)
	default:
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: fmt.Sprintf("unknown api name[%s]", param.Name),
		})
	}
}

// PutHALogs TODO
func PutHALogs(ctx *fasthttp.RequestCtx, setParam interface{}) {
	input := &model.HaLogs{}
	response := api.ResponseInfo{
		Data:    nil,
		Code:    api.RespOK,
		Message: "",
	}
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Code = api.RespErr
		response.Message = "must be POST method"
		return
	}
	// convert setParam
	if bytes, err := json.Marshal(setParam); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, input); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}

	db := model.HADB.Self.Table(input.TableName()).Create(input)
	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("insert table failed:%s", err.Error())
		return
	}

	response.Data = map[string]interface{}{api.RowsAffect: db.RowsAffected}
}
