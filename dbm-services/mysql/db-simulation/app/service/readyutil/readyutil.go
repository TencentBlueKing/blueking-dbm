/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package readyutil holds pure helpers for simulation cluster CREATE NODE readiness.
package readyutil

import "strings"

const (
	// SpiderBasePort is the first Spider listen port in the simulation pod.
	SpiderBasePort = 25000
	// BackendSimPort is the backend MySQL listen port in the simulation pod.
	BackendSimPort = 20000
)

// ClusterNodeProbePorts returns Spider ports (25000+idx) plus backend :20000.
func ClusterNodeProbePorts(spiderCount int) []int {
	if spiderCount < 0 {
		spiderCount = 0
	}
	ports := make([]int, 0, spiderCount+1)
	for idx := 0; idx < spiderCount; idx++ {
		ports = append(ports, SpiderBasePort+idx)
	}
	ports = append(ports, BackendSimPort)
	return ports
}

// IsCreateNodeSQL reports whether sql is a tdbctl CREATE NODE statement.
func IsCreateNodeSQL(sql string) bool {
	return strings.Contains(strings.ToLower(sql), "create node")
}

// IsRetryableCreateNodeError reports whether err is a transient CREATE NODE connect/autoinc failure.
func IsRetryableCreateNodeError(err error) bool {
	if err == nil {
		return false
	}
	msg := err.Error()
	return strings.Contains(msg, "12034") ||
		strings.Contains(msg, "Failed to connect to new server") ||
		strings.Contains(msg, "checking auto-increment")
}
