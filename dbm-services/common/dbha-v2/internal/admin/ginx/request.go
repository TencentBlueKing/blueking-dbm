/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - 微网关(BlueKing - Micro APIGateway) available.
 * Copyright (C) 2025 Tencent. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package ginx

import (
	"github.com/gin-gonic/gin"
	"github.com/spf13/cast"
)

const (
	minLimit  = 5
	maxLimit  = 100
	minOffset = 0
)

// GetLimit get limit
func GetLimit(c *gin.Context) int {
	limit := cast.ToInt(c.Query("limit"))
	limit = min(maxLimit, limit)
	limit = max(minLimit, limit)
	return limit
}

// GetOffset get offset
func GetOffset(c *gin.Context) int {
	offset := cast.ToInt(c.Query("offset"))
	offset = max(minOffset, offset)
	return offset
}
