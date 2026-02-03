/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package workflow

import (
	"fmt"
	"sort"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// FailureWindowEntry represents a merged failure event for one DB instance in the sliding window.
// Same instance (BkCloudID, IP, Port, DbType) is merged and Count is incremented.
type FailureWindowEntry struct {
	FailureInstanceInfo
	EventName       haprobe.DbEventName
	EventNameReason haprobe.DbEventNameReason
	Count           int       // number of failure occurrences in the window
	FirstAt         time.Time // first occurrence time in the window (used for slide-out)
}

// SlidingWindow is a time-based sliding window that caches detection failure events.
// Same DB instance (BkCloudID, IP, Port, DbType) is merged and Count is incremented on Push.
// Pop returns only entries that have slid out of the window (FirstAt + windowDuration < now).
// SlidingWindow is safe for concurrent use: Len uses a read lock; Push and Pop use a write lock.
type SlidingWindow struct {
	mu             sync.RWMutex
	windowDuration time.Duration
	byKey          map[string]*FailureWindowEntry
}

// NewSlidingWindow creates a time-based sliding window with the given duration.
// Entries older than (now - windowDuration) are considered "slid out" and returned by Pop.
func NewSlidingWindow(windowDuration time.Duration) *SlidingWindow {
	return &SlidingWindow{
		windowDuration: windowDuration,
		byKey:          make(map[string]*FailureWindowEntry),
	}
}

// Push adds a failure event into the window. If the same DB instance (BkCloudID, IP, Port, DbType)
// already exists in the window, it is merged and Count is incremented; otherwise a new entry is added.
// at is the occurrence time (typically time.Now()); entries with FirstAt before (now - windowDuration) will be returned by Pop(now).
func (w *SlidingWindow) Push(inst *FailureInstanceInfo, eventName haprobe.DbEventName,
	eventNameReason haprobe.DbEventNameReason, at time.Time) {
	key := instanceWindowKey(inst.BkCloudID, inst.IP, inst.Port, inst.DbType)

	w.mu.Lock()
	defer w.mu.Unlock()

	if e, ok := w.byKey[key]; ok {
		e.Count++
		return
	}

	w.byKey[key] = &FailureWindowEntry{
		FailureInstanceInfo: *inst,
		EventName:           eventName,
		EventNameReason:     eventNameReason,
		Count:               1,
		FirstAt:             at,
	}
}

// Pop returns all entries that have slid out of the window (FirstAt < now - windowDuration),
// and removes them from the window. Returned slice is sorted by FirstAt ascending.
func (w *SlidingWindow) Pop(now time.Time) []*FailureWindowEntry {
	w.mu.Lock()
	defer w.mu.Unlock()

	cutoff := now.Add(-w.windowDuration)

	var result []*FailureWindowEntry
	for k, e := range w.byKey {
		if e.FirstAt.Before(cutoff) {
			result = append(result, e)
			delete(w.byKey, k)
		}
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].FirstAt.Before(result[j].FirstAt)
	})

	return result
}

// Len returns the number of distinct instances currently in the window.
func (w *SlidingWindow) Len() int {
	w.mu.RLock()
	defer w.mu.RUnlock()

	return len(w.byKey)
}

// instanceWindowKey returns a unique key for the same DB instance (used for merge).
func instanceWindowKey(bkCloudID int, ip string, port int, dbType haprobe.DbType) string {
	return fmt.Sprintf("%d:%s:%d:%s", bkCloudID, ip, port, dbType)
}
