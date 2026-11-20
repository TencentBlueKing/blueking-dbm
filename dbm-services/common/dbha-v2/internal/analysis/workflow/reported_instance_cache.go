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
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	reportReasonHit          = "hit"
	reportReasonNoKey        = "no_key"
	reportReasonExpired      = "expired"
	reportReasonEventChanged = "event_changed"

	reportSourceCache = "memory"
	reportSourceDB    = "db"
)

// ReportCheckInfo describes why a failure instance is skipped or allowed before Push.
type ReportCheckInfo struct {
	Inst        string
	Event       haprobe.DbEventName
	CachedEvent haprobe.DbEventName
	SetAt       time.Time
	ExpireAt    time.Time
	TTL         time.Duration
	Remaining   time.Duration
	Reason      string
	Source      string
}

// ReportCacheEntry is one instance entry written into the reported cache. The caller
// decides SetAt and ExpireAt so a restored DB window can be inherited without renewal.
type ReportCacheEntry struct {
	EventName haprobe.DbEventName
	SetAt     time.Time
	ExpireAt  time.Time
}

// ReportedInstanceCache records instances already reported recently, so repeated failure
// events for them are dropped before entering the sliding window.
type ReportedInstanceCache struct {
	mu      sync.RWMutex
	entries map[string]ReportCacheEntry
}

// NewReportedInstanceCache creates an empty reported instance cache.
func NewReportedInstanceCache() *ReportedInstanceCache {
	return &ReportedInstanceCache{entries: make(map[string]ReportCacheEntry)}
}

// reportCacheKey identifies an instance for the cache.
func reportCacheKey(bkBizID, bkCloudID int, ip string, port int, dbType haprobe.DbType) string {
	return fmt.Sprintf("%d:%d:%s:%d:%s", bkBizID, bkCloudID, ip, port, dbType)
}

// CheckRecentReport reports whether an instance was already reported recently.
// A hit never refreshes the entry; an expired entry is removed lazily.
func (c *ReportedInstanceCache) CheckRecentReport(inst *FailureInstanceInfo) (bool, ReportCheckInfo) {
	info := ReportCheckInfo{
		Inst:   reportCacheKey(inst.BkBizID, inst.BkCloudID, inst.IP, inst.Port, inst.DbType),
		Event:  inst.EventName,
		Source: reportSourceCache,
	}

	c.mu.Lock()
	defer c.mu.Unlock()

	entry, ok := c.entries[info.Inst]
	if !ok {
		info.Reason = reportReasonNoKey
		return false, info
	}
	info.CachedEvent = entry.EventName
	info.SetAt = entry.SetAt
	info.ExpireAt = entry.ExpireAt
	info.TTL = entry.ExpireAt.Sub(entry.SetAt)

	if !time.Now().Before(entry.ExpireAt) {
		delete(c.entries, info.Inst)
		info.Reason = reportReasonExpired
		return false, info
	}

	info.Remaining = time.Until(entry.ExpireAt).Round(time.Second)
	if entry.EventName == inst.EventName {
		info.Reason = reportReasonHit
		return true, info
	}
	info.Reason = reportReasonEventChanged
	return false, info
}

// MarkReported records or refreshes instances that have already been reported, either
// in this round or by existing snapshot logs. Expired entries are removed using the
// caller's timestamp so instances whose failure has recovered do not stay forever.
func (c *ReportedInstanceCache) MarkReported(
	entries map[string]ReportCacheEntry,
	now time.Time,
) {
	c.mu.Lock()
	defer c.mu.Unlock()

	for key, entry := range c.entries {
		if !now.Before(entry.ExpireAt) {
			delete(c.entries, key)
		}
	}
	for key, entry := range entries {
		c.entries[key] = entry
	}
}

// logReported writes the common fields of a report-related trace log.
func logReported(prefix string, info ReportCheckInfo, bizID int, dbType haprobe.DbType) {
	logger.Info("%s, inst: %s, bizId: %d, dbType: %s, event: %s, cachedEvent: %s, "+
		"setAt: %s, expireAt: %s, ttl: %s, remaining: %s, source: %s",
		prefix, info.Inst, bizID, dbType, info.Event, info.CachedEvent,
		info.SetAt.Format(time.RFC3339), info.ExpireAt.Format(time.RFC3339),
		info.TTL, info.Remaining, info.Source)
}

// logReportedInstanceCheck writes a traceable log for an instance handled before Push.
func logReportedInstanceCheck(info ReportCheckInfo, bizID int, dbType haprobe.DbType) {
	var prefix string
	switch info.Reason {
	case reportReasonExpired:
		prefix = "reported instance cache entry expired, removed before push"
	case reportReasonHit:
		prefix = "skip push for already reported instance"
	case reportReasonEventChanged:
		prefix = "reported instance event changed, allow push"
	default:
		return
	}
	logReported(prefix, info, bizID, dbType)
}
