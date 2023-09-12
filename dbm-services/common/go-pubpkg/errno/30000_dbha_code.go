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
	// dbha code start 30000

	// ErrMultiMaster TODO
	// mysql error, prefix is 300
	ErrMultiMaster = &Errno{Code: 30001, Message: "Multi master found", CNMessage: "同一主机同时存在实例角色master和slave"}
	// ErrSwitchNumUnMatched TODO
	// dead host's instance num not equal to its switch number
	ErrSwitchNumUnMatched = &Errno{Code: 30002, Message: "instances number is %d, switch number is %d, unmatched",
		CNMessage: "实例个数%d与切换个数%d不匹配"}
	// ErrRemoteQuery TODO
	ErrRemoteQuery = &Errno{Code: 30003, Message: "do remote query failed", CNMessage: "调用remoteQuery失败"}
	// ErrRemoteExecute TODO
	ErrRemoteExecute = &Errno{Code: 30004, Message: "do remote execute failed", CNMessage: "调用remoteExecute失败"}
	// ErrIOTreadState TODO
	ErrIOTreadState = &Errno{Code: 30005, Message: "slave IO_THREAD is not ok", CNMessage: "IO_THREAD异常"}
	// ErrSQLTreadState TODO
	ErrSQLTreadState = &Errno{Code: 30006, Message: "slave SQL_THREAD is not ok", CNMessage: "SQL_THREAD异常"}
	// ErrSlaveStatus TODO
	ErrSlaveStatus = &Errno{Code: 30007, Message: "get slave status abnormal", CNMessage: "获取slave status异常"}
	// proxy error, prefix is 400

)
