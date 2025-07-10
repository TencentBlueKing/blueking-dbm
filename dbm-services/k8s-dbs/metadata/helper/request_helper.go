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

package helper

import (
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/core/entity"
	"k8s-dbs/errors"
	metaconst "k8s-dbs/metadata/constant"
	"strconv"

	"github.com/gin-gonic/gin"
)

// BuildPagination 构建 Pagination
func BuildPagination(ctx *gin.Context) (*commentity.Pagination, error) {
	page, err := strconv.Atoi(ctx.DefaultQuery(metaconst.ParamsPage, metaconst.DefaultPageStr))
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return nil, err
	}
	limit, err := strconv.Atoi(ctx.DefaultQuery(metaconst.ParamsLimit, metaconst.DefaultFetchSizeStr))
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataErr, err))
		return nil, err
	}
	limit = min(limit, metaconst.MaxFetchSize)
	pagination := commentity.Pagination{Page: page, Limit: limit}
	return &pagination, nil
}

// BuildPageParams 构建 Page Params
func BuildPageParams(ctx *gin.Context) map[string]interface{} {
	params := make(map[string]interface{})
	for key, values := range ctx.Request.URL.Query() {
		if key != metaconst.ParamsPage && key != metaconst.ParamsLimit {
			if len(values) > 0 {
				params[key] = values[0]
			}
		}
	}
	return params
}
