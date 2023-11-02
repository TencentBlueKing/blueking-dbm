/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package util

// LoggerErrorStack 在最外层遇到 error 时打印 stack 信息到日志
// err == nil 时不打印
// output 是个 logger，避免在 util 里引入 logger导致循环 import
func LoggerErrorStack(output func(format string, args ...interface{}), err error) {
	if err != nil {
		output("%+v", err)
	}
}
