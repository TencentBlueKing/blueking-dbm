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

// BlackWhiteListQueryParam 查询参数，使用指针类型支持bk_cloud_id=0
type BlackWhiteListQueryParam struct {
	ID            uint   `json:"id,omitempty"`
	BkBizID       *int   `json:"bk_biz_id,omitempty"`
	BkCloudID     *int   `json:"bk_cloud_id,omitempty"`
	ClusterID     *int   `json:"cluster_id,omitempty"`
	ClusterName   string `json:"cluster_name,omitempty"`
	SwitchVersion string `json:"switch_version,omitempty"`
	Status        string `json:"status,omitempty"`
}

// api name
const (
	// GetBlackWhiteList 查询黑白名单
	GetBlackWhiteList = "get_black_white_list"
	// PutBlackWhiteList 新增黑白名单
	PutBlackWhiteList = "insert_black_white_list"
	// UpdateBlackWhiteList 更新黑白名单
	UpdateBlackWhiteList = "update_black_white_list"
	// DeleteBlackWhiteList 删除黑白名单
	DeleteBlackWhiteList = "delete_black_white_list"
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
	case PutBlackWhiteList:
		InsertBlackWhiteList(ctx, param.SetArgs)
	case UpdateBlackWhiteList:
		UpdateBlackWhiteListHandler(ctx, param.QueryArgs, param.SetArgs)
	case DeleteBlackWhiteList:
		DeleteBlackWhiteListHandler(ctx, param.QueryArgs)
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
		whereCond = &BlackWhiteListQueryParam{}
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

	db := model.HADB.Self.Table(model.HABlackWhiteList{}.TableName())
	if whereCond.BkBizID != nil {
		db = db.Where("bk_biz_id = ?", *whereCond.BkBizID)
	}
	if whereCond.BkCloudID != nil {
		db = db.Where("bk_cloud_id = ?", *whereCond.BkCloudID)
	}
	if whereCond.ClusterID != nil {
		db = db.Where("cluster_id = ?", *whereCond.ClusterID)
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

// InsertBlackWhiteList 新增黑白名单记录
func InsertBlackWhiteList(ctx *fasthttp.RequestCtx, setParam interface{}) {
	input := &model.HABlackWhiteList{}
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

	// 转换参数
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

	// 校验必填字段（bk_cloud_id允许为0，所以不校验）
	if input.BkBizID == 0 || input.ClusterID == 0 || input.ClusterName == "" {
		response.Code = api.RespErr
		response.Message = "bk_biz_id, cluster_id and cluster_name must be specified"
		return
	}
	if input.SwitchVersion == "" {
		response.Code = api.RespErr
		response.Message = "switch_version must be specified"
		return
	}
	if input.Status == "" {
		input.Status = model.StatusEnabled
	}

	log.Logger.Infof("InsertBlackWhiteList param: bk_biz_id=%d, bk_cloud_id=%d, cluster_id=%d, "+
		"cluster_name=%s, switch_version=%s, status=%s",
		input.BkBizID, input.BkCloudID, input.ClusterID, input.ClusterName, input.SwitchVersion, input.Status)

	db := model.HADB.Self.Table(input.TableName()).Create(input)
	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("insert black white list table failed:%s", err.Error())
		return
	}

	response.Data = map[string]interface{}{
		api.RowsAffect: db.RowsAffected,
		"id":           input.ID,
	}
	log.Logger.Infof("InsertBlackWhiteList success, id=%d", input.ID)
}

// UpdateBlackWhiteListHandler 更新黑白名单记录
func UpdateBlackWhiteListHandler(ctx *fasthttp.RequestCtx, queryParam interface{}, setParam interface{}) {
	var (
		result   = map[string]int64{}
		query    = &BlackWhiteListQueryParam{}
		setArgs  = &model.HABlackWhiteList{}
		response = api.ResponseInfo{
			Data:    &result,
			Code:    api.RespOK,
			Message: "",
		}
	)
	defer func() { api.SendResponse(ctx, response) }()

	if !ctx.IsPost() {
		response.Message = "must be POST request"
		response.Code = api.RespErr
		return
	}

	// 转换查询条件
	if bytes, err := json.Marshal(queryParam); err != nil {
		log.Logger.Errorf("convert query param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, query); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}

	// 转换更新内容
	if bytes, err := json.Marshal(setParam); err != nil {
		log.Logger.Errorf("convert set param failed:%s", err.Error())
		response.Code = api.RespErr
		response.Message = err.Error()
		return
	} else {
		if err = json.Unmarshal(bytes, setArgs); err != nil {
			response.Code = api.RespErr
			response.Message = err.Error()
			return
		}
	}

	// 查询条件不能为空，防止全表更新
	if query.ID == 0 && query.BkBizID == nil && query.ClusterID == nil &&
		query.ClusterName == "" {
		response.Code = api.RespErr
		response.Message = "query_args must specify at least one of: id, bk_biz_id, cluster_id, cluster_name"
		return
	}

	log.Logger.Infof("UpdateBlackWhiteList query:%+v, set:%+v", query, setArgs)

	db := model.HADB.Self.Table(model.HABlackWhiteList{}.TableName())
	if query.ID != 0 {
		db = db.Where("id = ?", query.ID)
	}
	if query.BkBizID != nil {
		db = db.Where("bk_biz_id = ?", *query.BkBizID)
	}
	if query.BkCloudID != nil {
		db = db.Where("bk_cloud_id = ?", *query.BkCloudID)
	}
	if query.ClusterID != nil {
		db = db.Where("cluster_id = ?", *query.ClusterID)
	}
	if query.ClusterName != "" {
		db = db.Where("cluster_name = ?", query.ClusterName)
	}
	if query.SwitchVersion != "" {
		db = db.Where("switch_version = ?", query.SwitchVersion)
	}
	db = db.Updates(setArgs)
	if err := db.Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("update black white list table failed:%s", err.Error())
		return
	}
	result[api.RowsAffect] = db.RowsAffected
	log.Logger.Infof("UpdateBlackWhiteList success, rowsAffected=%d", db.RowsAffected)
}

// DeleteBlackWhiteListHandler 删除黑白名单记录
func DeleteBlackWhiteListHandler(ctx *fasthttp.RequestCtx, queryParam interface{}) {
	var (
		result    = map[string]int64{}
		whereCond = &BlackWhiteListQueryParam{}
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
		return
	}

	// 转换查询条件
	if bytes, err := json.Marshal(queryParam); err != nil {
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

	// 删除条件不能为空，防止全表删除
	if whereCond.ID == 0 && whereCond.BkBizID == nil && whereCond.ClusterID == nil &&
		whereCond.ClusterName == "" {
		response.Code = api.RespErr
		response.Message = "query_args must specify at least one of: id, bk_biz_id, cluster_id, cluster_name"
		return
	}

	log.Logger.Infof("DeleteBlackWhiteList param:%+v", whereCond)

	db := model.HADB.Self.Table(model.HABlackWhiteList{}.TableName())
	if whereCond.ID != 0 {
		db = db.Where("id = ?", whereCond.ID)
	}
	if whereCond.BkBizID != nil {
		db = db.Where("bk_biz_id = ?", *whereCond.BkBizID)
	}
	if whereCond.BkCloudID != nil {
		db = db.Where("bk_cloud_id = ?", *whereCond.BkCloudID)
	}
	if whereCond.ClusterID != nil {
		db = db.Where("cluster_id = ?", *whereCond.ClusterID)
	}
	if whereCond.ClusterName != "" {
		db = db.Where("cluster_name = ?", whereCond.ClusterName)
	}
	if whereCond.SwitchVersion != "" {
		db = db.Where("switch_version = ?", whereCond.SwitchVersion)
	}

	if err := db.Delete(&model.HABlackWhiteList{}).Error; err != nil {
		response.Code = api.RespErr
		response.Message = err.Error()
		response.Data = nil
		log.Logger.Errorf("delete black white list table failed:%s", err.Error())
		return
	}
	result[api.RowsAffect] = db.RowsAffected
	log.Logger.Infof("DeleteBlackWhiteList success, rowsAffected=%d", db.RowsAffected)
}
