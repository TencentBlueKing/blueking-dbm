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
	coreconst "k8s-dbs/common/api/constant"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/core/provider"

	"github.com/gin-gonic/gin"
)

// ComponentController 存储集群管理 Controller
type ComponentController struct {
	componentProvider *provider.ComponentProvider
}

// NewComponentController 创建 ClusterController 实例
func NewComponentController(componentProvider *provider.ComponentProvider) *ComponentController {
	return &ComponentController{
		componentProvider,
	}
}

// DescribeComponent 查看组件详情
func (c *ComponentController) DescribeComponent(ctx *gin.Context) {
	request := &coreentity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeComponentError, err))
		return
	}
	responseData, err := c.componentProvider.DescribeComponent(request)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeComponentError, err))
		return
	}
	coreentity.SuccessResponse(ctx, responseData, coreconst.Success)
}
