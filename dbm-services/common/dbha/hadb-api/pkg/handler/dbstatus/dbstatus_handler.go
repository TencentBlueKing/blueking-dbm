package dbstatus

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/pkg/api"

	"github.com/valyala/fasthttp"
)

const (
	// GetStatus TODO
	GetStatus = "get_instance_status"
	// UpdateStatus TODO
	UpdateStatus = "update_instance_status"
	// PutStatus TODO
	PutStatus = "insert_instance_status"
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
	case GetStatus:
		GetDBStatus(ctx, param.QueryArgs)
	case UpdateStatus:
		UpdateDBStatus(ctx, param.QueryArgs, param.SetArgs)
	case PutStatus:
		PutDBStatus(ctx, param.SetArgs)
	default:
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: fmt.Sprintf("unknown api name[%s]", param.Name),
		})
	}
}

// GetDBStatus TODO
func GetDBStatus(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		result    = []model.DbStatus{}
		whereCond = &model.DbStatus{}
		response  = api.ResponseInfo{
			Data:    &result,
			Code:    api.RespOK,
			Message: "",
		}
	)
	// NB:couldn't user api.SendResponse(ctx, response) directly, otherwise
	// deepCopy response first
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Message = "must be Post request"
		response.Code = api.RespErr
		log.Logger.Errorf("must by post request, param:%+v", param)
		return
	}

	if bytes, err := json.Marshal(param); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, whereCond); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}
	log.Logger.Debugf("%+v", whereCond)

	if err := model.HADB.Self.Table(whereCond.TableName()).Where(whereCond).Find(&result).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", result)
}

// UpdateDBStatus TODO
func UpdateDBStatus(ctx *fasthttp.RequestCtx, queryParam interface{}, setParam interface{}) {
	var (
		result    = map[string]int64{}
		whereCond = struct {
			query model.DbStatus
			set   model.DbStatus
		}{}
		response = api.ResponseInfo{
			Data:    &result,
			Code:    api.RespOK,
			Message: "",
		}
	)

	// NB:couldn't user api.SendResponse(ctx, response) directly, otherwise
	// deepCopy response first
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Message = "must be POST request"
		response.Code = api.RespErr
		return
	}

	// convert queryParam
	if bytes, err := json.Marshal(queryParam); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, &whereCond.query); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}

	// convert setParam
	if bytes, err := json.Marshal(setParam); err != nil {
		log.Logger.Errorf("convert param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, &whereCond.set); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}
	whereCond.set.LastTime = time.Now()
	log.Logger.Debugf("%+v", whereCond)

	db := model.HADB.Self.Table(whereCond.query.TableName()).Where(whereCond.query).Updates(whereCond.set)
	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	result[api.RowsAffect] = db.RowsAffected
	log.Logger.Debugf("%+v", result)
	return
}

// PutDBStatus TODO
func PutDBStatus(ctx *fasthttp.RequestCtx, setParam interface{}) {
	input := &model.DbStatus{}
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
