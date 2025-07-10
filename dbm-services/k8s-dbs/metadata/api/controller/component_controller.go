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
	"k8s-dbs/errors"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/resp"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ComponentController manages the metadata for component.
type ComponentController struct {
	componentProvider provider.K8sCrdComponentProvider
}

// NewComponentController creates a new instance of ComponentController
func NewComponentController(componentProvider provider.K8sCrdComponentProvider) *ComponentController {
	return &ComponentController{componentProvider}
}

// GetComponent get an existing component by its ID.
func (c *ComponentController) GetComponent(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	component, err := c.componentProvider.FindComponentByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.K8sCrdComponentRespVo
	if err := copier.Copy(&data, component); err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}
