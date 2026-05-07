/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package marker 提供 dbactuator 在 stdout 上输出结构化事件行的统一协议。
//
// 协议格式：每条 marker 占独立一行，固定前缀 + 单行 JSON 载荷，例如
//
//	__DBACTUATOR_EVENT__ {"ts":"2026-05-07T02:11:00Z","event":"exec_db_begin","db":"mydb"}
//
// 设计目标：
//  1. 与 mysql client 的 stdout 回显（如 -vvv）共存，前缀必须足够独特，不会出现在业务 SQL 中。
//  2. 字段后向兼容扩展，老消费端忽略未知字段即可。
//  3. 流式按行解析友好：begin/end 成对，最后一段也有边界。
//
// 消费端（dbm-ui backend）按行扫描，匹配 Prefix 后用 json.loads 解析剩余载荷。
package marker

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

// Prefix 是 dbactuator 写到 stdout 的事件行前缀，消费端按此前缀切行。
const Prefix = "__DBACTUATOR_EVENT__"

// 已定义的事件类型常量。新增类型时统一加在这里，避免 typo。
const (
	EventExecDBBegin = "exec_db_begin"
	EventExecDBEnd   = "exec_db_end"
)

// Event 是 stdout 上一条结构化事件的载荷。
//
// 新增字段必须 omitempty，保持后向兼容；老消费端会忽略未知字段。
type Event struct {
	Ts    string `json:"ts"`
	Event string `json:"event"`
	DB    string `json:"db,omitempty"`
	Err   string `json:"err,omitempty"`
}

// Emit 把一条事件写到 stdout（独立一行）。
//
// 调用方负责保证调用顺序与业务执行顺序一致（例如 begin 在子命令启动前、
// end 在子命令返回后），不要把 Emit 放进 goroutine 以避免行序错乱。
func Emit(e Event) {
	if e.Ts == "" {
		e.Ts = time.Now().UTC().Format(time.RFC3339)
	}
	b, err := json.Marshal(e)
	if err != nil {
		return
	}
	fmt.Fprintf(os.Stdout, "%s %s\n", Prefix, b)
}
