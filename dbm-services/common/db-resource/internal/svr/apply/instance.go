/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package apply

import "dbm-services/common/db-resource/internal/model"

// InstanceObject TODO
type InstanceObject struct {
	BkHostId        int
	Equipment       string
	LinkNetdeviceId []string
	Nice            int64
	InsDetail       *model.TbRpDetail
}

// GetLinkNetDeviceIdsInterface TODO
func (c *InstanceObject) GetLinkNetDeviceIdsInterface() []interface{} {
	var k []interface{}
	for _, v := range c.LinkNetdeviceId {
		k = append(k, v)
	}
	return k
}

// Wrapper TODO
type Wrapper struct {
	Instances []InstanceObject
	by        func(p, q *InstanceObject) bool
}

// SortBy TODO
type SortBy func(p, q *InstanceObject) bool

// Len 用于排序
func (pw Wrapper) Len() int { // 重写 Len() 方法
	return len(pw.Instances)
}

// Swap 用于排序
func (pw Wrapper) Swap(i, j int) { // 重写 Swap() 方法
	pw.Instances[i], pw.Instances[j] = pw.Instances[j], pw.Instances[i]
}

// Less 用于排序
func (pw Wrapper) Less(i, j int) bool { // 重写 Less() 方法
	return pw.by(&pw.Instances[i], &pw.Instances[j])
}
