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
	"fmt"
	coreconst "k8s-dbs/core/constant"
)

// GetDefaultNameSpace 根据业务ID、业务简称以及存储类型生成默认的命名空间名称
func GetDefaultNameSpace(bkBizID uint64, bkAppAbbr string, addonType string) string {
	// 获取存储类型简称
	addonAbbr := coreconst.GetStorageAddonAbbr(coreconst.StorageAddonType(addonType))

	// 生成命名空间名称，格式: <存储简称>-<业务简称>-<业务ID>
	return fmt.Sprintf("%s-%s-%d", addonAbbr, bkAppAbbr, bkBizID)
}
