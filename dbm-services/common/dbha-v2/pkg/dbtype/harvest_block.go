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

package dbtype

import (
	"fmt"
	"strings"
	"sync"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// NormalizeBlockName folds a harvester block name to its canonical form.
// viper lowercases bare map keys, so every block name must pass through this.
func NormalizeBlockName(name string) string { return strings.ToLower(name) }

// EndpointAttrs are the routing-relevant attributes of a probe endpoint.
type EndpointAttrs struct {
	ClusterType  haprobe.DbmMetadataClusterType
	MachineType  haprobe.DbmMetadataMachineType
	InstanceRole haprobe.DbmMetadataInstanceRole
	AccessLayer  haprobe.DbmMetadataAccessLayerType
	Ip           string
	Ports        []string
	AdminPorts   []string
}

// PortKind selects which port fields a routed endpoint should carry.
type PortKind uint8

const (
	// PortKindAll keeps both Ports and AdminPorts.
	PortKindAll PortKind = iota
	// PortKindData keeps Ports only; AdminPorts must stay nil.
	PortKindData
	// PortKindAdmin keeps AdminPorts only; Ports must stay nil.
	PortKindAdmin
)

// EndpointRoute is one harvester block destination for an endpoint.
type EndpointRoute struct {
	BlockName string
	Ports     PortKind
}

// EndpointRouter maps endpoint attributes to zero or more harvester blocks.
// Returning multiple routes enables dual-produce (e.g. mysql-proxy admin + data).
type EndpointRouter func(EndpointAttrs) []EndpointRoute

// HarvestBlock describes a probe harvester config block for genconfig routing.
// A single DbType may own multiple blocks (e.g. mysql + mysqlProxyAdmin).
// Match selects among blocks for the same DbType; nil Match is the fallback block.
type HarvestBlock struct {
	BlockName  string
	DbType     haprobe.DbType
	PayloadKey string
	Match      func(EndpointAttrs) bool
}

var (
	harvestBlockMu        sync.RWMutex
	harvestBlocksByDbType = map[haprobe.DbType][]HarvestBlock{}
	harvestBlockByName    = map[string]HarvestBlock{}

	endpointRouterMu sync.RWMutex
	endpointRouters  = map[haprobe.DbType]EndpointRouter{}
)

// RegisterHarvestBlock registers a harvest block descriptor.
// Panics on duplicate BlockName (compared after NormalizeBlockName) or when a
// second nil-Match fallback is registered for the same DbType.
// BlockName keeps its original casing for YAML/logs; the registry key is normalized.
func RegisterHarvestBlock(b HarvestBlock) {
	if b.BlockName == "" {
		panic("dbtype: refuse to register HarvestBlock with empty BlockName")
	}
	if b.DbType == haprobe.DbTypeNone || b.DbType == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("dbtype: refuse to register HarvestBlock with invalid DbType: %q", b.DbType))
	}

	norm := NormalizeBlockName(b.BlockName)

	harvestBlockMu.Lock()
	defer harvestBlockMu.Unlock()

	if _, exists := harvestBlockByName[norm]; exists {
		panic(fmt.Sprintf("dbtype: duplicate HarvestBlock BlockName: %s", b.BlockName))
	}
	if b.Match == nil {
		for _, existing := range harvestBlocksByDbType[b.DbType] {
			if existing.Match == nil {
				panic(fmt.Sprintf(
					"dbtype: DbType %s already has a nil-Match fallback block %q",
					b.DbType, existing.BlockName,
				))
			}
		}
	}
	harvestBlockByName[norm] = b
	harvestBlocksByDbType[b.DbType] = append(harvestBlocksByDbType[b.DbType], b)
}

// HarvestBlocksOf returns harvest blocks registered for the given DbType.
func HarvestBlocksOf(dt haprobe.DbType) []HarvestBlock {
	harvestBlockMu.RLock()
	defer harvestBlockMu.RUnlock()
	src := harvestBlocksByDbType[dt]
	if len(src) == 0 {
		return nil
	}
	out := make([]HarvestBlock, len(src))
	copy(out, src)
	return out
}

// HarvestBlockByName looks up a harvest block by its config block name.
// The lookup key is normalized so camelCase and lowercase names match.
func HarvestBlockByName(name string) (HarvestBlock, bool) {
	harvestBlockMu.RLock()
	defer harvestBlockMu.RUnlock()
	b, ok := harvestBlockByName[NormalizeBlockName(name)]
	return b, ok
}

// RegisterEndpointRouter registers a DbType-specific endpoint router.
// Panics on nil router, invalid DbType, or duplicate registration.
func RegisterEndpointRouter(dt haprobe.DbType, r EndpointRouter) {
	if r == nil {
		panic(fmt.Sprintf("dbtype: refuse to register nil EndpointRouter for DbType: %q", dt))
	}
	if dt == haprobe.DbTypeNone || dt == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("dbtype: refuse to register EndpointRouter with invalid DbType: %q", dt))
	}

	endpointRouterMu.Lock()
	defer endpointRouterMu.Unlock()

	if _, exists := endpointRouters[dt]; exists {
		panic(fmt.Sprintf("dbtype: duplicate EndpointRouter for DbType: %s", dt))
	}
	endpointRouters[dt] = r
}

// RouteEndpoint resolves harvester destinations for one endpoint.
// Prefer a registered EndpointRouter; otherwise fall back to HarvestBlock Match /
// nil-Match, returning a single PortKindAll route. Unknown DbType (or no blocks)
// returns an empty slice without logging.
func RouteEndpoint(dt haprobe.DbType, attrs EndpointAttrs) []EndpointRoute {
	if dt == haprobe.DbTypeNone || dt == haprobe.DbTypeUnknown {
		return nil
	}

	endpointRouterMu.RLock()
	router, hasRouter := endpointRouters[dt]
	endpointRouterMu.RUnlock()
	if hasRouter {
		return router(attrs)
	}

	blocks := HarvestBlocksOf(dt)
	if len(blocks) == 0 {
		return nil
	}

	matchAttrs := EndpointAttrs{
		ClusterType:  attrs.ClusterType,
		MachineType:  attrs.MachineType,
		InstanceRole: attrs.InstanceRole,
		AccessLayer:  attrs.AccessLayer,
	}

	var fallback *HarvestBlock
	for i := range blocks {
		b := &blocks[i]
		if b.Match == nil {
			fallback = b
			continue
		}
		if b.Match(matchAttrs) {
			return []EndpointRoute{{BlockName: b.BlockName, Ports: PortKindAll}}
		}
	}
	if fallback != nil {
		return []EndpointRoute{{BlockName: fallback.BlockName, Ports: PortKindAll}}
	}
	logger.Info(
		"skip endpoint with no matching harvest block, db_type: %s, cluster_type: %s, access_layer: %s",
		dt, attrs.ClusterType, attrs.AccessLayer,
	)
	return nil
}

// EndpointRouterDbTypes returns DbTypes that registered an EndpointRouter.
func EndpointRouterDbTypes() []haprobe.DbType {
	endpointRouterMu.RLock()
	defer endpointRouterMu.RUnlock()
	out := make([]haprobe.DbType, 0, len(endpointRouters))
	for dt := range endpointRouters {
		out = append(out, dt)
	}
	return out
}
