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
	"context"
	"encoding/json"
	"sort"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// InstanceDiscovery fetches and watches the list of analysis instances from etcd for business sharding.
type InstanceDiscovery struct {
	discovery      *discovery.Discovery
	registryPrefix string
	myServiceID    string
	instanceIDs    []string
	instanceIDsMu  sync.RWMutex
	quit           chan struct{}
}

// NewInstanceDiscovery creates an InstanceDiscovery. quit is shared with the workflow for lifecycle.
func NewInstanceDiscovery(disc *discovery.Discovery, registryPrefix, myServiceID string, quit chan struct{}) *InstanceDiscovery {
	return &InstanceDiscovery{
		discovery:      disc,
		registryPrefix: registryPrefix,
		myServiceID:    myServiceID,
		quit:           quit,
	}
}

// RefreshList fetches the current list of analysis instances from etcd and updates instanceIDs.
func (d *InstanceDiscovery) RefreshList(ctx context.Context) {
	if d.discovery == nil {
		return
	}
	ctx2, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	kvs, err := d.discovery.GetWithPrefix(ctx2, d.registryPrefix)
	if err != nil {
		logger.Warn("failed to get analysis instances from etcd, fallback to single instance, errmsg: %s", err)
		d.instanceIDsMu.Lock()
		d.instanceIDs = []string{d.myServiceID}
		d.instanceIDsMu.Unlock()
		return
	}

	var ids []string
	for _, v := range kvs {
		var info discovery.ServiceInfo
		if err := json.Unmarshal(v, &info); err != nil {
			continue
		}
		if info.ID != "" {
			ids = append(ids, info.ID)
		}
	}

	if len(ids) == 0 {
		ids = []string{d.myServiceID}
	}

	sort.Strings(ids)
	d.instanceIDsMu.Lock()
	prev := d.instanceIDs
	d.instanceIDs = ids
	d.instanceIDsMu.Unlock()

	if len(prev) != len(ids) || (len(prev) > 0 && prev[0] != ids[0]) {
		logger.Info("analysis instance list updated, count: %d, ids: %v", len(ids), ids)
	}
}

// RunWatch watches etcd for registry changes and refreshes the instance list.
// The caller is responsible for goroutine lifecycle (e.g. WaitGroup Add/Done if used).
func (d *InstanceDiscovery) RunWatch(ctx context.Context) {
	if d.discovery == nil {
		return
	}

	watchChan, err := d.discovery.WatchWithPrefix(ctx, d.registryPrefix)
	if err != nil {
		logger.Warn("failed to watch analysis instances, errmsg: %s", err)
		return
	}

	d.RefreshList(ctx)

	for {
		select {
		case <-d.quit:
			return
		case <-ctx.Done():
			return
		case _, ok := <-watchChan:
			if !ok {
				return
			}
			d.RefreshList(ctx)
		}
	}
}

// AssignedBizIDs returns the subset of allBizIDs assigned to this instance (even sharding by instance list).
func (d *InstanceDiscovery) AssignedBizIDs(allBizIDs []int) []int {
	d.instanceIDsMu.RLock()
	ids := make([]string, len(d.instanceIDs))
	copy(ids, d.instanceIDs)
	d.instanceIDsMu.RUnlock()

	N := len(ids)
	if N == 0 {
		return allBizIDs
	}

	myIdx := -1
	for i, id := range ids {
		if id == d.myServiceID {
			myIdx = i
			break
		}
	}
	if myIdx < 0 {
		return allBizIDs
	}

	sorted := make([]int, len(allBizIDs))
	copy(sorted, allBizIDs)
	sort.Ints(sorted)

	var out []int
	for i, bizID := range sorted {
		if i%N == myIdx {
			out = append(out, bizID)
		}
	}
	return out
}
