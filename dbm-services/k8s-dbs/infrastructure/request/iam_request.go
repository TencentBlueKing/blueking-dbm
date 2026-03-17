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

package request

// SimpleCheckAllowedRequest 对应 DBM /iam/simple_check_allowed/ 的请求体
// 用户身份通过 X-Bkapi-Authorization 请求头传递
type SimpleCheckAllowedRequest struct {
	ActionID         string `json:"action_id"`
	BkBizID          int    `json:"bk_biz_id,omitempty"`
	ResourceID       string `json:"resource_id"`
	IsRaiseException bool   `json:"is_raise_exception"`
}
