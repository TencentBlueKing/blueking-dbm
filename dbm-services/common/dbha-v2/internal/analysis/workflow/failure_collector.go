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

	"dbm-services/common/dbha-v2/internal/analysis/detector"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// FailureInstanceInfo represents one instance that detector marked as failure (needs switching).
type FailureInstanceInfo struct {
	BkCloudID int
	IP        string
	Port      int
	BkBizID   int
	Cluster   string
	ClusterID int
	DbType    haprobe.DbType
}

// FailureGroup groups failure instances by (BkCloudID, DbType) for batch switching.
type FailureGroup struct {
	BkCloudID       int
	DbType          haprobe.DbType
	Instances       []FailureInstanceInfo
	EventName       haprobe.DbEventName       // event type that led to this failure (for strategy matching)
	EventNameReason haprobe.DbEventNameReason // event reason (for strategy matching)
}

// IPs returns the list of IPs for building switcher request (deduplicated).
func (g *FailureGroup) IPs() []string {
	seen := make(map[string]struct{}, len(g.Instances))
	ips := make([]string, 0, len(g.Instances))
	for _, inst := range g.Instances {
		if _, ok := seen[inst.IP]; ok {
			continue
		}
		seen[inst.IP] = struct{}{}
		ips = append(ips, inst.IP)
	}
	return ips
}

// FailureCollector collects detector failure responses and groups them by (BkCloudID, DbType).
type FailureCollector struct {
	groups map[string]*FailureGroup // key: "bkCloudId:dbType"
}

// NewFailureCollector creates a new FailureCollector.
func NewFailureCollector() *FailureCollector {
	return &FailureCollector{groups: make(map[string]*FailureGroup)}
}

// Add adds a detector failure response into the collector.
func (c *FailureCollector) Add(resp *detector.Response) {
	meta := resp.Meta
	key := fmt.Sprintf("%d:%s", meta.BkCloudID, resp.DbType)
	info := FailureInstanceInfo{
		BkCloudID: meta.BkCloudID,
		IP:        meta.IP,
		Port:      meta.Port,
		BkBizID:   meta.BkBizID,
		Cluster:   meta.Cluster,
		ClusterID: meta.ClusterID,
		DbType:    resp.DbType,
	}

	if g, ok := c.groups[key]; ok {
		g.Instances = append(g.Instances, info)
		return
	}

	c.groups[key] = &FailureGroup{
		BkCloudID:       meta.BkCloudID,
		DbType:          resp.DbType,
		Instances:       []FailureInstanceInfo{info},
		EventName:       resp.DbEventName,
		EventNameReason: resp.DbEventNameReason,
	}
}

// Empty returns true if no failure group was collected.
func (c *FailureCollector) Empty() bool {
	return len(c.groups) == 0
}

// Groups returns all failure groups in deterministic order (by BkCloudID, then DbType).
func (c *FailureCollector) Groups() []*FailureGroup {
	if len(c.groups) == 0 {
		return nil
	}
	keys := make([]string, 0, len(c.groups))
	for k := range c.groups {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := make([]*FailureGroup, 0, len(keys))
	for _, k := range keys {
		out = append(out, c.groups[k])
	}
	return out
}
