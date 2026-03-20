/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import "time"

// LLM 相关超时常量
// 使用较长的超时时间以支持 LLM 思考型模型（dsv32-thinking 等），这些模型可能需要数分钟才能返回结果
const (
	// LLMAnalysisTimeout Agent 分析任务超时时间，与配置的 timeout_seconds 默认值一致
	LLMAnalysisTimeout = 360 * time.Second
	// LLMHTTPClientTimeout HTTP 客户端超时时间，需大于 LLMAnalysisTimeout 以便 context 先取消
	LLMHTTPClientTimeout = 420 * time.Second
)
