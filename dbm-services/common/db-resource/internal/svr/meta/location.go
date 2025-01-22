/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package meta

import "dbm-services/common/go-pubpkg/cmutil"

// LocationSpec location spec param
type LocationSpec struct {
	City             string   `json:"city" validate:"required"` // 所属城市获取地域
	SubZoneIds       []string `json:"sub_zone_ids"`
	IncludeOrExclude *bool    `json:"include_or_exclue"`
}

// IsEmpty whether the address location parameter is blank
func (l LocationSpec) IsEmpty() bool {
	return cmutil.IsEmpty(l.City)
}

// SubZoneIsEmpty determine whether subzone is empty
func (l LocationSpec) SubZoneIsEmpty() bool {
	return l.IsEmpty() || len(l.SubZoneIds) == 0
}

// IsExclude TODO
func (l LocationSpec) IsExclude() bool {
	if l.IncludeOrExclude == nil {
		return false
	}
	return !*l.IncludeOrExclude
}
