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

package response

// BkbaseBizResponse bk-base 网关 /v4/meta/bizs/ 接口响应
type BkbaseBizResponse struct {
	Result  bool            `json:"result"`
	Code    string          `json:"code"` // bk-base 返回字符串，如 "00"
	Data    []BkbaseBizItem `json:"data"`
	Message *string         `json:"message"` // 可能为 null
	Errors  interface{}     `json:"errors"`
}

// BkbaseBizItem 业务条目，仅提取 bk_biz_id 用于校验
type BkbaseBizItem struct {
	BkBizID uint64 `json:"bk_biz_id"`
}
