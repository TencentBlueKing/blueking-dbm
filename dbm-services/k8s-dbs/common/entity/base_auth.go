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

// Package entity 定义 common 模块使用的通用实体类型
package entity

// BKAdditional 封装请求附加信息（认证授权 + 业务控制参数）
type BKAdditional struct {
	BkAppCode   string `json:"bk_app_code,omitempty"`
	BkAppSecret string `json:"bk_app_secret,omitempty"`
	BkUserName  string `json:"bk_username,omitempty" binding:"required" msg:"bk_username 字段不能为空"`
	AsyncToDbm  *bool  `json:"async_to_dbm,omitempty"`
}

// ShouldAsyncToDBM 返回是否需要同步到 DBM；nil 视为 false（默认关闭）
func (a *BKAdditional) ShouldAsyncToDBM() bool {
	if a == nil || a.AsyncToDbm == nil {
		return false
	}
	return *a.AsyncToDbm
}
