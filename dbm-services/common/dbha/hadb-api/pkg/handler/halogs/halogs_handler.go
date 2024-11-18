/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

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
	input := &model.HaGMLogs{}
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

	response.Data = map[string]interface{}{
		api.RowsAffect: db.RowsAffected,
		"uid":          input.Uid,
	}
}
