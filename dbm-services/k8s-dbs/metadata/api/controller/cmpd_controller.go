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

// CmpdController manages the metadata for Cmpd
type CmpdController struct {
	cmpdProvider provider.K8sCrdCmpdProvider
}

// NewCmpdController creates a new instance of Cmpd
func NewCmpdController(cmpdProvider provider.K8sCrdCmpdProvider) *CmpdController {
	return &CmpdController{cmpdProvider}
}

// GetCmpd retrieves a cmpd by its ID
func (c *CmpdController) GetCmpd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cd, err := c.cmpdProvider.FindCmpdByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.K8sCrdCmpdRespVo
	if err := copier.Copy(&data, cd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateCmpd creates a new cmpd.
func (c *CmpdController) CreateCmpd(ctx *gin.Context) {
	var cmpd req.K8sCrdCmpdReqVo
	if err := ctx.ShouldBindJSON(&cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var cmpdEntity entitys.K8sCrdComponentDefinitionEntity
	if err := copier.Copy(&cmpdEntity, &cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	added, err := c.cmpdProvider.CreateCmpd(&cmpdEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.K8sCrdCmpdRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// UpdateCmpd updates an existing cmpd.
func (c *CmpdController) UpdateCmpd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpd req.K8sCrdCmpdReqVo
	if err := ctx.ShouldBindJSON(&cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpdEntity entitys.K8sCrdComponentDefinitionEntity
	if err := copier.Copy(&cmpdEntity, cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	cmpdEntity.ID = id
	rows, err := c.cmpdProvider.UpdateCmpd(&cmpdEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}

// DeleteCmpd deletes an cmpd by its ID.
func (c *CmpdController) DeleteCmpd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	rows, err := c.cmpdProvider.DeleteCmpdByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}
