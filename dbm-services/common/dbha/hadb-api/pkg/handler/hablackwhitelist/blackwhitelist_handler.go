/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package hablackwhitelist

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/dbha/hadb-api/log"
	"dbm-services/common/dbha/hadb-api/model"
	"dbm-services/common/dbha/hadb-api/pkg/api"

	"github.com/valyala/fasthttp"
)

// api name
const (
	// GetBlackWhiteList 查询黑白名单
	GetBlackWhiteList = "get_black_white_list"
)

// Handler 黑白名单请求处理入口
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
	case GetBlackWhiteList:
		QueryBlackWhiteList(ctx, param.QueryArgs)
	default:
		api.SendResponse(ctx, api.ResponseInfo{
			Data:    nil,
			Code:    api.RespErr,
			Message: fmt.Sprintf("unknown api name[%s]", param.Name),
		})
	}
}

// QueryBlackWhiteList 查询黑白名单，判断指定集群是否在黑名单中
func QueryBlackWhiteList(ctx *fasthttp.RequestCtx, param interface{}) {
	var (
		result    = []model.HABlackWhiteList{}
		whereCond = &model.HABlackWhiteList{}
		response  = api.ResponseInfo{
			Data:    &result,
			Code:    api.RespOK,
			Message: "",
		}
	)
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Message = "must be POST request"
		response.Code = api.RespErr
		log.Logger.Errorf("must be post request, param:%+v", param)
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
	log.Logger.Debugf("QueryBlackWhiteList param:%+v", whereCond)

	db := model.HADB.Self.Table(whereCond.TableName())
	if whereCond.BkBizID != 0 {
		db = db.Where("bk_biz_id = ?", whereCond.BkBizID)
	}
	if whereCond.BkCloudID != 0 {
		db = db.Where("bk_cloud_id = ?", whereCond.BkCloudID)
	}
	if whereCond.ClusterID != 0 {
		db = db.Where("cluster_id = ?", whereCond.ClusterID)
	}
	if whereCond.ClusterName != "" {
		db = db.Where("cluster_name = ?", whereCond.ClusterName)
	}
	if whereCond.SwitchVersion != "" {
		db = db.Where("switch_version = ?", whereCond.SwitchVersion)
	}
	if whereCond.Status != "" {
		db = db.Where("status = ?", whereCond.Status)
	}

	if err := db.Find(&result).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("query black white list table failed:%s", err.Error())
	}
	log.Logger.Debugf("QueryBlackWhiteList result:%+v", result)
}
