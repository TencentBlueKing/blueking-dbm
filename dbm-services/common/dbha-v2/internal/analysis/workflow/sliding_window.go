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

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// FailureWindowEntry represents a merged failure event for one DB instance and one event in the
// sliding window. Same instance (BkCloudID, IP, Port, DbType) with the same event is merged and
// Count is incremented.
type FailureWindowEntry struct {
	FailureInstanceInfo
	FirstAt time.Time // first occurrence time in the window (used for slide-out)
}

// BizWindowManager manages per-BizID sliding windows and instance-level inflight marks.
// Inflight marks are keyed by instance (bkCloudID:ip:port:dbType) to prevent duplicate switching
// at the finest granularity without affecting other instances in the same business.
type BizWindowManager struct {
	mu             sync.RWMutex
	windowDuration time.Duration
	inflightTTL    time.Duration
	windows        map[int]*slidingWindow // key = BizID
	inflight       map[string]time.Time   // key = instanceKey (bkCloudID:ip:port:dbType), value = inflight mark timestamp
	myServiceID    string
}

// NewBizWindowManager creates a BizWindowManager with the given window duration and inflight TTL.
// windowDuration controls how long entries stay in the window before being eligible for Pop.
// inflightTTL is the maximum time an inflight mark is valid; expired marks are automatically cleaned up
// to prevent permanent blocking if MarkDone is not called (e.g. goroutine panic).
func NewBizWindowManager(windowDuration, inflightTTL time.Duration, serviceID string) *BizWindowManager {
	return &BizWindowManager{
		windowDuration: windowDuration,
		inflightTTL:    inflightTTL,
		windows:        make(map[int]*slidingWindow),
		inflight:       make(map[string]time.Time),
		myServiceID:    serviceID,
	}
}

// Push adds a failure event into the window of the given BizID.
// Before pushing, it checks whether the instance is marked as inflight (switching in progress).
// If inflight, the event is discarded and a log is recorded; returns false.
// Otherwise the event is merged into the window; returns true.
func (m *BizWindowManager) Push(bizId int, inst *FailureInstanceInfo, at time.Time) bool {
	key := instanceWindowKey(inst.BkCloudID, inst.IP, inst.Port, inst.DbType)

	m.mu.Lock()
	defer m.mu.Unlock()

	// Check if the instance is switching (inflight); if so, discard and log
	if startAt, ok := m.inflight[key]; ok {
		if time.Since(startAt) < m.inflightTTL {
			logger.Info("instance is switching (inflight), discard push, inst: %s, bizId: %d, inflightSince: %v",
				key, bizId, startAt.Format(time.RFC3339))
			return false
		}
		// Inflight mark has expired, auto cleanup
		logger.Warn("inflight mark expired, auto cleanup, inst: %s, bizId: %d, inflightSince: %v, ttl: %v",
			key, bizId, startAt.Format(time.RFC3339), m.inflightTTL)
		delete(m.inflight, key)
	}

	w := m.getOrCreateWindowLocked(bizId)
	w.push(inst, at)
	return true
}

// Pop returns all entries that have slid out of the window for the given BizID
// (FirstAt + windowDuration < now), and removes them from the window.
// Returned slice is sorted by FirstAt ascending.
func (m *BizWindowManager) Pop(bizId int, now time.Time) []*FailureWindowEntry {
	m.mu.Lock()
	defer m.mu.Unlock()

	w, ok := m.windows[bizId]
	if !ok {
		return nil
	}

	result := w.pop(now)

	// If the window is empty, clean up the business window to free memory
	if w.len() == 0 {
		delete(m.windows, bizId)
	}

	return result
}

// PopAndMarkStart atomically pops matured entries for a business and marks each instance as inflight.
// This avoids the race window where a new Push may happen between popping and inflight marking.
func (m *BizWindowManager) PopAndMarkStart(bizId int, now time.Time) []*FailureWindowEntry {
	m.mu.Lock()
	defer m.mu.Unlock()

	w, ok := m.windows[bizId]
	if !ok {
		return nil
	}

	result := w.pop(now)
	for _, entry := range result {
		key := instanceWindowKey(entry.BkCloudID, entry.IP, entry.Port, entry.DbType)
		m.inflight[key] = now
	}

	// If the window is empty, clean up the business window to free memory
	if w.len() == 0 {
		delete(m.windows, bizId)
	}

	return result
}

// MarkDone removes the inflight mark for the given instance key, indicating that switching has completed.
// This re-enables Push for the instance.
func (m *BizWindowManager) MarkDone(instanceKey string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	delete(m.inflight, instanceKey)
}

// getOrCreateWindowLocked returns the sliding window for the given BizID, creating one if it does not exist.
// Caller must hold m.mu.
func (m *BizWindowManager) getOrCreateWindowLocked(bizId int) *slidingWindow {
	w, ok := m.windows[bizId]
	if !ok {
		w = newSlidingWindow(m.windowDuration, bizId, m.myServiceID)
		m.windows[bizId] = w
	}
	return w
}

// WindowLen returns the number of entries in the window for the given BizID.
// It is safe to call concurrently.
func (m *BizWindowManager) WindowLen(bizId int) int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if w, ok := m.windows[bizId]; ok {
		return w.len()
	}
	return 0
}

// slidingWindow is a time-based sliding window that caches detection failure events.
// Same DB instance (BkCloudID, IP, Port, DbType) with the same event is merged and Count is
// incremented on push. pop returns only entries that have slid out of the window
// (FirstAt + windowDuration < now).
// slidingWindow is NOT safe for concurrent use; callers must hold the BizWindowManager lock.
type slidingWindow struct {
	windowDuration time.Duration
	bizId          int
	byKey          map[string]*FailureWindowEntry
	myServiceID    string
}

// newSlidingWindow creates a time-based sliding window with the given duration.
func newSlidingWindow(windowDuration time.Duration, bizId int, serviceID string) *slidingWindow {
	return &slidingWindow{
		windowDuration: windowDuration,
		bizId:          bizId,
		byKey:          make(map[string]*FailureWindowEntry),
		myServiceID:    serviceID,
	}
}

// push adds a failure event into the window. If the same instance and event already exists,
// it is merged and Count is incremented; otherwise a new entry is added.
func (w *slidingWindow) push(inst *FailureInstanceInfo, at time.Time) {
	key := instanceWindowEventKey(inst.BkCloudID, inst.IP, inst.Port, inst.DbType, inst.EventName)

	// merge into the existing entry: increment Count but keep FirstAt unchanged,
	// so the entry slides out of the window based on its first occurrence time.
	if e, ok := w.byKey[key]; ok {
		e.Count++
		return
	}

	// new entry: the first occurrence, so Count starts at 1.
	entry := &FailureWindowEntry{
		FailureInstanceInfo: *inst,
		FirstAt:             at,
	}
	entry.Count = 1
	w.byKey[key] = entry
}

// pop returns all entries that have slid out of the window (FirstAt < now - windowDuration),
// and removes them from the window. Returned slice is sorted by FirstAt ascending.
func (w *slidingWindow) pop(now time.Time) []*FailureWindowEntry {
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

// len returns the number of distinct instance+event entries currently in the window.
func (w *slidingWindow) len() int {
	return len(w.byKey)
}

// instanceWindowKey returns a unique key for the same DB instance (used for inflight tracking).
func instanceWindowKey(bkCloudID int, ip string, port int, dbType haprobe.DbType) string {
	return fmt.Sprintf("%d:%s:%d:%s", bkCloudID, ip, port, dbType)
}

// instanceWindowEventKey returns a unique key for the same instance and event, so that the same
// instance reporting different events are kept as separate entries in the window.
func instanceWindowEventKey(bkCloudID int, ip string, port int, dbType haprobe.DbType, eventName haprobe.DbEventName) string {
	return fmt.Sprintf("%d:%s:%d:%s:%s", bkCloudID, ip, port, dbType, eventName)
}
