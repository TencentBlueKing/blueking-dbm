// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// procRoot is replaced in tests, which have no instance process.
var procRoot = "/proc"

// clockTicks is USER_HZ, the unit of /proc/<pid>/stat times: 100 on every Linux the actuator runs on.
const clockTicks = 100

// ProcessByArg finds the process with an argument holding arg, e.g. an instance by the path of
// its redis.conf, and returns its pid and start time, which tells a restarted process apart.
func ProcessByArg(arg string) (int, uint64, error) {
	entries, err := os.ReadDir(procRoot)
	if err != nil {
		return 0, 0, err
	}
	for _, e := range entries {
		pid, err := strconv.Atoi(e.Name())
		if err != nil {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(procRoot, e.Name(), "cmdline"))
		if err != nil {
			continue
		}
		for _, a := range bytes.Split(raw, []byte{0}) {
			if bytes.Contains(a, []byte(arg)) {
				_, start, err := processStat(pid)
				return pid, start, err
			}
		}
	}
	return 0, 0, fmt.Errorf("no process runs with %s", arg)
}

// processStat reads a process's user plus system CPU and its start time in clock ticks.
func processStat(pid int) (time.Duration, uint64, error) {
	raw, err := os.ReadFile(filepath.Join(procRoot, strconv.Itoa(pid), "stat"))
	if err != nil {
		return 0, 0, err
	}
	// The command name is in parentheses and may hold spaces; fields count on from its end.
	end := bytes.LastIndexByte(raw, ')')
	if end < 0 {
		return 0, 0, fmt.Errorf("unexpected /proc/%d/stat", pid)
	}
	fields := strings.Fields(string(raw[end+1:]))
	// fields[0] is field 3 (state): utime is 14, stime 15, starttime 22.
	if len(fields) < 20 {
		return 0, 0, fmt.Errorf("unexpected /proc/%d/stat: %d fields", pid, len(fields)+2)
	}
	utime, err1 := strconv.ParseUint(fields[11], 10, 64)
	stime, err2 := strconv.ParseUint(fields[12], 10, 64)
	start, err3 := strconv.ParseUint(fields[19], 10, 64)
	if err1 != nil || err2 != nil || err3 != nil {
		return 0, 0, fmt.Errorf("unexpected /proc/%d/stat times", pid)
	}
	return time.Duration(utime+stime) * time.Second / clockTicks, start, nil
}

// processCPU is pid's CPU so far, provided it is still the process that started at start.
func processCPU(pid int, start uint64) (time.Duration, error) {
	cpu, got, err := processStat(pid)
	if err != nil {
		return 0, err
	}
	if got != start {
		return 0, fmt.Errorf("pid %d was restarted", pid)
	}
	return cpu, nil
}
