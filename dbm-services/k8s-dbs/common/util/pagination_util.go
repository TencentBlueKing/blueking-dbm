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

package util

import (
	"k8s-dbs/common/constant"
	"k8s-dbs/common/entity"
)

// Paginate 服务端分页查询
func Paginate[T any](
	pagination *entity.Pagination,
	data []T,
) ([]T, error) {
	page := pagination.Page
	limit := pagination.Limit
	if page < 1 {
		page = constant.DefaultPage
	}
	if limit < 1 {
		limit = constant.DefaultPageLimit
	}
	start := (page - 1) * limit
	if start >= len(data) {
		return []T{}, nil
	}
	end := start + limit
	if end > len(data) {
		end = len(data)
	}
	return data[start:end], nil
}
