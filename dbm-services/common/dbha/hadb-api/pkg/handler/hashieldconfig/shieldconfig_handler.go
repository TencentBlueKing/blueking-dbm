/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package hashieldconfig

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/pkg/api"

	"github.com/valyala/fasthttp"
)

// api name
const (
	// GetShieldInfo get shield config info
	GetShieldInfo = "get_shield_info"
	// PutShieldInfo insert shield config info
	PutShieldInfo = "insert_shield_info"
	// UpdateShieldInfo update shield config info
	UpdateShieldInfo = "update_shield_info"
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
	case GetShieldInfo:
		GetShieldConfig(ctx, param.QueryArgs)
	case UpdateShieldInfo:
		UpdateShieldConfig(ctx, param.QueryArgs, param.SetArgs)
	case PutShieldInfo:
		PutShieldConfig(ctx, param.SetArgs)
	default:
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: fmt.Sprintf("unknown api name[%s]", param.Name),
		})
	}
}

// GetShieldConfig select shield config from table
func GetShieldConfig(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		result    = []model.HAShield{}
		whereCond = &model.HAShield{}
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
		response.Message = "must be POST request"
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

	currentTime := time.Now()
	db := model.HADB.Self.Table(whereCond.TableName())
	if whereCond.APP != "" {
		db = db.Where("app = ?", whereCond.APP)
	}
	if whereCond.StartTime != nil && !whereCond.StartTime.IsZero() {
		db = db.Where("start_time > ?", whereCond.StartTime)
	} else {
		db = db.Where("start_time < ?", currentTime)
	}
	if whereCond.EndTime != nil && !whereCond.EndTime.IsZero() {
		db = db.Where("end_time < ?", whereCond.EndTime)
	} else {
		db = db.Where("end_time > ?", currentTime)
	}
	if whereCond.ShieldType != "" {
		db = db.Where("shield_type = ?", whereCond.ShieldType)
	}

	if err := db.Find(&result).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query table failed:%s", err.Error())
	}
	log.Logger.Debugf("%+v", result)
}

// PutShieldConfig insert shield config to table
func PutShieldConfig(ctx *fasthttp.RequestCtx, setParam interface{}) {
	input := &model.HAShield{}
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
	if input.APP == "" || input.Ip == "" {
		response.Code = api.RespErr
		response.Message = "app and ip must specified"
		return
	}

	db := model.HADB.Self.Table(input.TableName()).Create(input)
	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("insert table failed:%s", err.Error())
		return
	}

	response.Data = map[string]interface{}{
		api.RowsAffect: db.RowsAffected,
		"uid":          input.Uid,
	}
}

// UpdateShieldConfig TODO
func UpdateShieldConfig(ctx *fasthttp.RequestCtx, queryParam interface{}, setParam interface{}) {
	var (
		result    = map[string]int64{}
		whereCond = struct {
			query model.HAShield
			set   model.HAShield
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
