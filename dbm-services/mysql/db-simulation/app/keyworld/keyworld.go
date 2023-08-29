/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package keyworld TODO
package keyworld

import (
	"dbm-services/common/go-pubpkg/cmutil"
)

// ALL_KEYWORD TODO
var ALL_KEYWORD []string

func init() {
	ALL_KEYWORD = append(ALL_KEYWORD, MySQL55_KEYWORD...)
	ALL_KEYWORD = append(ALL_KEYWORD, MySQL56_KEYWORD...)
	ALL_KEYWORD = append(ALL_KEYWORD, MySQL57_KEYWORD...)
	ALL_KEYWORD = append(ALL_KEYWORD, MySQL80_KEYWORD...)
	ALL_KEYWORD = cmutil.RemoveDuplicate(ALL_KEYWORD)
}
