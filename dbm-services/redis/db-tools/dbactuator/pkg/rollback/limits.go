// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"runtime"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

// Limits are the per-stage concurrency of one host, sized from its CPUs and available memory.
// Stages use different resources, so each has its own bound instead of the tightest one for all.
type Limits struct {
	CPU int
	// Unpack bounds unpacking full backups and, for SSD, restoring rocksdb and starting.
	Unpack int
	// MemAvailable is MemAvailable from /proc/meminfo at node start, 0 when unknown.
	MemAvailable int64
	// Max is the payload's max_concurrency; 0 leaves every stage at what the host allows.
	Max int
}

// HostLimits reads the host. maxConcurrency only lowers the limits, never raises them.
func HostLimits(maxConcurrency int) Limits {
	l := Limits{CPU: runtime.NumCPU(), Max: maxConcurrency}
	if mem, err := readMemAvailable(); err == nil {
		l.MemAvailable = mem
	} else {
		mylog.Logger.Warn("read MemAvailable failed, memory window disabled: %v", err)
	}
	l.Unpack = l.capped(l.CPU / 2)
	return l
}

func (l Limits) capped(n int) int {
	if l.Max > 0 && n > l.Max {
		n = l.Max
	}
	if n < 1 {
		n = 1
	}
	return n
}

// Replay is the number of SSD ports replaying binlogs at once. A replaying port spends most of
// its time decompressing and decoding, and takes a core only while sending, so up to one port
// per core.
func (l Limits) Replay(ports int) int {
	return l.capped(min(ports, l.CPU))
}

// KvstoreReplay is the number of Tendisplus kvstores replaying at once. Each runs binlog_tool and
// its writes into the instance together, so it stays at one per two cores.
func (l Limits) KvstoreReplay(streams int) int {
	return l.capped(min(streams, l.CPU/2))
}

// Loading bounds Cache instances loading at once, each taking one core.
func (l Limits) Loading() int {
	return l.capped(l.CPU)
}

func (l Limits) String() string {
	return fmt.Sprintf("cpu=%d unpack=%d loading=%d mem_available=%s max_concurrency=%d",
		l.CPU, l.Unpack, l.Loading(), humanBytes(l.MemAvailable), l.Max)
}

func readMemAvailable() (int64, error) {
	f, err := os.Open("/proc/meminfo")
	if err != nil {
		return 0, err
	}
	defer f.Close()
	return parseMemAvailable(f)
}

func parseMemAvailable(r io.Reader) (int64, error) {
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) >= 2 && fields[0] == "MemAvailable:" {
			kb, err := strconv.ParseInt(fields[1], 10, 64)
			if err != nil {
				return 0, err
			}
			return kb * 1024, nil
		}
	}
	if err := scanner.Err(); err != nil {
		return 0, err
	}
	return 0, fmt.Errorf("no MemAvailable in /proc/meminfo")
}

func humanBytes(n int64) string {
	const unit = 1024
	if n < unit {
		return fmt.Sprintf("%dB", n)
	}
	div, exp := int64(unit), 0
	for m := n / unit; m >= unit; m /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f%ciB", float64(n)/float64(div), "KMGTPE"[exp])
}
