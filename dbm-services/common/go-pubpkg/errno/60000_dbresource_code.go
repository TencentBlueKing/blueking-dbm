/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package errno

var (
	// dbresource code start  60000

	// ErrResourceinsufficient TODO
	ErrResourceinsufficient = Errno{Code: 60001, Message: "resource insufficient", CNMessage: "资源不足"}
	// ErrResourceLock TODO
	ErrResourceLock = Errno{Code: 60002, Message: "failed to acquire resource lock", CNMessage: "获取资源锁失败"}
	// ErrApplyResourceParamCheck TODO
	ErrApplyResourceParamCheck = Errno{Code: 60003, Message: "failed to check the parameters of the applied resource",
		CNMessage: "申请资源参数合法性检查不通过"}
	// ErresourceLockReturn TODO
	ErresourceLockReturn = Errno{Code: 6004, CNMessage: "锁定机器,返回机器失败",
		Message: "failed to lock the machine and return the machine"}
)
