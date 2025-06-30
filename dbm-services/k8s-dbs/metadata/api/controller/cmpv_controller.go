/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controller

import (
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/metadata/api/vo/req"
	"k8s-dbs/metadata/api/vo/resp"
	"k8s-dbs/metadata/provider"
	entitys "k8s-dbs/metadata/provider/entity"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// CmpvController manages the metadata for cmpv.
type CmpvController struct {
	cmpvProvider provider.K8sCrdCmpvProvider
}

// NewCmpvController creates a new instance of CmpvController.
func NewCmpvController(cmpvProvider provider.K8sCrdCmpvProvider) *CmpvController {
	return &CmpvController{cmpvProvider}
}

// GetCmpv get cmpv by its id.
func (c *CmpvController) GetCmpv(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cd, err := c.cmpvProvider.FindCmpvByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.K8sCrdCmpvRespVo
	if err := copier.Copy(&data, cd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateCmpv creates a new cmpv
func (c *CmpvController) CreateCmpv(ctx *gin.Context) {
	var cmpv req.K8sCrdCmpvReqVo
	if err := ctx.ShouldBindJSON(&cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var cmpvEntity entitys.K8sCrdComponentVersionEntity
	if err := copier.Copy(&cmpvEntity, &cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	added, err := c.cmpvProvider.CreateCmpv(&cmpvEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.K8sCrdCmpvRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// UpdateCmpv updates an existing cmpv.
func (c *CmpvController) UpdateCmpv(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpv req.K8sCrdCmpvReqVo
	if err := ctx.ShouldBindJSON(&cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpvEntity entitys.K8sCrdComponentVersionEntity
	if err := copier.Copy(&cmpvEntity, cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	cmpvEntity.ID = id
	rows, err := c.cmpvProvider.UpdateCmpv(&cmpvEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}

// DeleteCmpv delete an cmpv by its ID.
func (c *CmpvController) DeleteCmpv(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	rows, err := c.cmpvProvider.DeleteCmpvID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}
