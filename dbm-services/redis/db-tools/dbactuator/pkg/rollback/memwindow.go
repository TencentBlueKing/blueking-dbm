// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

// Resident memory per byte of a Cache data file, as the planner estimates it.
const (
	memoryRatioRDB = 2.0
	memoryRatioAOF = 2.0
)

// memReserveDivisor keeps a tenth of MemAvailable out of the window for the OS and page cache.
// The flow's memory precheck mirrors it as MEMORY_RESERVE_DIVISOR.
const memReserveDivisor = 10

// CacheMemory is the estimated resident memory of a Cache instance loading dataBytes.
func CacheMemory(dataBytes int64, isAOF bool) int64 {
	ratio := memoryRatioRDB
	if isAOF {
		ratio = memoryRatioAOF
	}
	return int64(float64(dataBytes) * ratio)
}

// SSDMemory is what a TendisSSD instance keeps resident whatever its data size: the block cache
// plus rocksdb's default two write buffers, read from its redis.conf.
func SSDMemory(confFile string) int64 {
	raw, err := os.ReadFile(confFile)
	if err != nil {
		return 0
	}
	var blockCache, writeBuffer int64
	for _, line := range strings.Split(string(raw), "\n") {
		fields := strings.Fields(line)
		if len(fields) != 2 {
			continue
		}
		v, err := strconv.ParseInt(fields[1], 10, 64)
		if err != nil {
			continue
		}
		switch fields[0] {
		case "rocksdb_block_cache":
			blockCache = v
		case "rocksdb_write_buffer_size":
			writeBuffer = v
		}
	}
	return blockCache + 2*writeBuffer
}

// memWindow admits instances while the memory they will hold fits the host. A Cache port starts
// as soon as it fits, and finishing a load frees the gap between the estimate and the real RSS
// for the next one; ports are never batched behind each other.
type memWindow struct {
	mu         sync.Mutex
	cond       *sync.Cond
	budget     int64
	used       int64
	loading    int
	maxLoading int
}

// newMemWindow returns a window over memAvailable; 0 means unknown and admits by CPU only.
func newMemWindow(memAvailable int64, maxLoading int) *memWindow {
	w := &memWindow{budget: memAvailable - memAvailable/memReserveDivisor, maxLoading: maxLoading}
	w.cond = sync.NewCond(&w.mu)
	return w
}

func (w *memWindow) fits(need int64) bool {
	return w.budget <= 0 || w.used+need <= w.budget
}

// acquire blocks until need fits and a loading slot is free. Loaded instances keep their memory,
// so when nothing is loading the window can no longer grow and a port that does not fit fails.
func (w *memWindow) acquire(need int64) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	for !w.fits(need) || w.loading >= w.maxLoading {
		if !w.fits(need) && w.loading == 0 {
			return fmt.Errorf("not enough memory: needs %s, %s of %s already taken",
				humanBytes(need), humanBytes(w.used), humanBytes(w.budget))
		}
		w.cond.Wait()
	}
	w.used += need
	w.loading++
	return nil
}

// admit takes memory for an instance already running, e.g. one a retry resumes.
func (w *memWindow) admit(need int64) {
	w.mu.Lock()
	w.used += need
	w.loading++
	w.mu.Unlock()
}

// loaded settles a finished load at its real resident size when that is known and smaller.
func (w *memWindow) loaded(reserved, actual int64) {
	w.mu.Lock()
	if actual > 0 && actual < reserved {
		w.used -= reserved - actual
	}
	w.loading--
	w.cond.Broadcast()
	w.mu.Unlock()
}

// release gives back everything a failed instance took.
func (w *memWindow) release(reserved int64) {
	w.mu.Lock()
	w.used -= reserved
	w.loading--
	w.cond.Broadcast()
	w.mu.Unlock()
}

// reserve takes memory that is never given back and does not hold a loading slot, for SSD
// instances whose caches are resident from startup.
func (w *memWindow) reserve(need int64) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if !w.fits(need) {
		return fmt.Errorf("not enough memory: needs %s, %s of %s already taken",
			humanBytes(need), humanBytes(w.used), humanBytes(w.budget))
	}
	w.used += need
	return nil
}

func confFile(instDir string) string {
	return filepath.Join(instDir, "redis.conf")
}
