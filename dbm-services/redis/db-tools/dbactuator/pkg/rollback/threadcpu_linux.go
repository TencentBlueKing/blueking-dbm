// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"syscall"
	"time"
)

// rusageThread is RUSAGE_THREAD, which the syscall package leaves out.
const rusageThread = 1

// threadCPU is the user and system time of the calling OS thread, falling back to the whole
// process when the thread cannot be read. It only tells a goroutine's CPU while that goroutine
// is locked to its thread.
func threadCPU() time.Duration {
	var ru syscall.Rusage
	if err := syscall.Getrusage(rusageThread, &ru); err != nil {
		return selfCPU()
	}
	return time.Duration(ru.Utime.Nano() + ru.Stime.Nano())
}
