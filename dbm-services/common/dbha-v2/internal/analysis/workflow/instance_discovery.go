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
	"fmt"
	"hash/crc32"
	"sort"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	// defaultReplicas is the number of virtual nodes per instance on the hash ring.
	// 200 provides a good balance between load distribution and memory usage.
	defaultReplicas = 200
)

// InstanceDiscovery fetches and watches the list of analysis instances from etcd for business sharding.
// It uses consistent hashing to minimize business redistribution when instances are added or removed.
type InstanceDiscovery struct {
	discovery      *discovery.Discovery
	registryPrefix string
	myServiceID    string
	hashRing       *consistentHash
	hashRingMu     sync.RWMutex
	quit           chan struct{}
}

// NewInstanceDiscovery creates an InstanceDiscovery. quit is shared with the workflow for lifecycle.
func NewInstanceDiscovery(
	disc *discovery.Discovery, registryPrefix, myServiceID string, quit chan struct{},
) *InstanceDiscovery {
	return &InstanceDiscovery{
		discovery:      disc,
		registryPrefix: registryPrefix,
		myServiceID:    myServiceID,
		hashRing:       newConsistentHash(defaultReplicas),
		quit:           quit,
	}
}

// RefreshList fetches the current list of analysis instances from etcd and rebuilds the hash ring.
func (d *InstanceDiscovery) RefreshList(ctx context.Context) {
	if d.discovery == nil {
		return
	}

	ctx2, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	kvs, err := d.discovery.GetWithPrefix(ctx2, d.registryPrefix)
	if err != nil {
		logger.Warn("failed to get analysis instances from etcd, fallback to single instance, errmsg: %s", err)

		d.hashRingMu.Lock()
		d.hashRing.rebuild([]string{d.myServiceID})
		d.hashRingMu.Unlock()

		return
	}

	logger.Debugf("get the list of analysis instances from etcd with prefix: %s, inst-count: %d",
		d.registryPrefix, len(kvs))

	var ids []string

	for _, v := range kvs {
		var info discovery.ServiceInfo
		if err := json.Unmarshal(v, &info); err != nil {
			logger.Warn("failed to unmarshal service info, info: %s, errmsg: %s", string(v), err)
			continue
		}

		if info.ID == "" {
			logger.Warn("service info id is empty, info: %s", string(v))
			continue
		}

		ids = append(ids, info.ID)
		logger.Debugf("analysis instance: %s, id: %s", info.Name, info.ID)
	}

	if len(ids) == 0 {
		ids = []string{d.myServiceID}
	}

	d.hashRingMu.Lock()
	prevSize := d.hashRing.size()
	d.hashRing.rebuild(ids)
	newSize := d.hashRing.size()
	d.hashRingMu.Unlock()

	if prevSize != newSize {
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

// AssignedBizIDs returns the subset of allBizIDs assigned to this instance
// using consistent hashing. This minimizes business redistribution when
// instances are added or removed (approximately 1/N redistribution vs N-1/N
// with modulo sharding).
func (d *InstanceDiscovery) AssignedBizIDs(allBizIDs []int) []int {
	d.hashRingMu.RLock()
	defer d.hashRingMu.RUnlock()

	if d.hashRing == nil || d.hashRing.size() == 0 {
		return allBizIDs
	}

	var out []int

	for _, bizID := range allBizIDs {
		owner := d.hashRing.get(strconv.Itoa(bizID))
		if owner == d.myServiceID {
			out = append(out, bizID)
		}
	}

	return out
}

// consistentHash implements consistent hashing with virtual nodes for business sharding.
// It minimizes business redistribution when instances are added or removed.
type consistentHash struct {
	replicas int               // number of virtual nodes per instance
	ring     []uint32          // sorted hash values on the ring
	nodes    map[uint32]string // hash value -> instance ID
}

// newConsistentHash creates a consistent hash ring with the given number of replicas.
func newConsistentHash(replicas int) *consistentHash {
	if replicas <= 0 {
		replicas = defaultReplicas
	}

	return &consistentHash{
		replicas: replicas,
		nodes:    make(map[uint32]string),
	}
}

// hashKey computes the CRC32 hash of the given key.
func (c *consistentHash) hashKey(key string) uint32 {
	return crc32.ChecksumIEEE([]byte(key))
}

// add adds an instance to the hash ring with virtual nodes.
func (c *consistentHash) add(instanceID string) {
	for i := 0; i < c.replicas; i++ {
		key := fmt.Sprintf("%s#%d", instanceID, i)
		hash := c.hashKey(key)
		c.ring = append(c.ring, hash)
		c.nodes[hash] = instanceID
	}
}

// get returns the instance ID responsible for the given key.
// It finds the first node clockwise from the key's hash position on the ring.
func (c *consistentHash) get(key string) string {
	if len(c.ring) == 0 {
		return ""
	}

	hash := c.hashKey(key)

	// Binary search for the first node with hash >= key's hash
	idx := sort.Search(len(c.ring), func(i int) bool {
		return c.ring[i] >= hash
	})

	// Wrap around to the first node if we've gone past the end
	if idx >= len(c.ring) {
		idx = 0
	}

	return c.nodes[c.ring[idx]]
}

// rebuild rebuilds the hash ring from a list of instance IDs.
// It clears the existing ring and adds all instances.
func (c *consistentHash) rebuild(instanceIDs []string) {
	c.ring = nil
	c.nodes = make(map[uint32]string)

	for _, id := range instanceIDs {
		c.add(id)
	}

	sort.Slice(c.ring, func(i, j int) bool {
		return c.ring[i] < c.ring[j]
	})
}

// size returns the number of virtual nodes on the ring.
func (c *consistentHash) size() int {
	return len(c.ring)
}
