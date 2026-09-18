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

// Package dbtype provides a centralized catalog mapping DbmMetadataClusterType to DbType.
package dbtype

import (
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Descriptor describes a DbType and the cluster types that map to it.
type Descriptor struct {
	DbType       haprobe.DbType
	ClusterTypes []haprobe.DbmMetadataClusterType
}

var (
	catalogMu       sync.RWMutex
	byClusterType   = map[haprobe.DbmMetadataClusterType]haprobe.DbType{}
	byDbType        = map[haprobe.DbType][]haprobe.DbmMetadataClusterType{}
	registeredTypes = map[haprobe.DbType]struct{}{}
	builtinTypes    = map[haprobe.DbType]struct{}{}
	providerTypes   = map[haprobe.DbType]struct{}{}
)

// registerBuiltin registers a placeholder mapping that a provider may later take over.
func registerBuiltin(d Descriptor) {
	register(d, true)
}

// Register registers a provider-owned mapping. It takes over the builtin placeholder
// for the same DbType; conflicting provider-vs-provider registrations still panic.
// On takeover, the provider ClusterTypes set must be a superset of the builtin set.
func Register(d Descriptor) {
	register(d, false)
}

func register(d Descriptor, builtin bool) {
	if d.DbType == haprobe.DbTypeNone || d.DbType == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("dbtype: refuse to register invalid DbType: %q", d.DbType))
	}
	if len(d.ClusterTypes) == 0 {
		panic(fmt.Sprintf("dbtype: refuse to register empty ClusterTypes for DbType: %s", d.DbType))
	}

	catalogMu.Lock()
	defer catalogMu.Unlock()

	takeover := false
	if _, exists := registeredTypes[d.DbType]; exists {
		_, isPlaceholder := builtinTypes[d.DbType]
		if builtin || !isPlaceholder {
			panic(fmt.Sprintf("dbtype: duplicate DbType registration: %s", d.DbType))
		}
		takeover = true

		// Superset check: every existing cluster type must remain mapped.
		newSet := make(map[haprobe.DbmMetadataClusterType]struct{}, len(d.ClusterTypes))
		for _, ct := range d.ClusterTypes {
			newSet[ct] = struct{}{}
		}
		for _, ct := range byDbType[d.DbType] {
			if _, ok := newSet[ct]; !ok {
				panic(fmt.Sprintf(
					"dbtype: takeover of %s would drop cluster type %s (provider set must be a superset)",
					d.DbType, ct,
				))
			}
		}
	}

	// Cross-type conflict check: exclude this DbType's own old mappings on takeover.
	for _, ct := range d.ClusterTypes {
		existing, ok := byClusterType[ct]
		if !ok {
			continue
		}
		if takeover && existing == d.DbType {
			continue
		}
		panic(fmt.Sprintf(
			"dbtype: duplicate cluster type %s (already mapped to %s, now %s)",
			ct, existing, d.DbType,
		))
	}

	// Commit: clear old mappings on takeover, then write the new descriptor.
	if takeover {
		for _, ct := range byDbType[d.DbType] {
			delete(byClusterType, ct)
		}
		delete(builtinTypes, d.DbType)
	}

	registeredTypes[d.DbType] = struct{}{}
	clusterTypes := make([]haprobe.DbmMetadataClusterType, len(d.ClusterTypes))
	copy(clusterTypes, d.ClusterTypes)
	byDbType[d.DbType] = clusterTypes
	for _, ct := range clusterTypes {
		byClusterType[ct] = d.DbType
	}
	if builtin {
		builtinTypes[d.DbType] = struct{}{}
	} else {
		providerTypes[d.DbType] = struct{}{}
	}
}

// DbTypeOf returns the DbType for the given cluster type.
// Unknown cluster types map to DbTypeNone (same as the previous GetDbType default).
func DbTypeOf(ct haprobe.DbmMetadataClusterType) haprobe.DbType {
	catalogMu.RLock()
	defer catalogMu.RUnlock()
	if dt, ok := byClusterType[ct]; ok {
		return dt
	}
	return haprobe.DbTypeNone
}

// ClusterTypesOf returns a copy of cluster types registered for the given DbType.
func ClusterTypesOf(dt haprobe.DbType) []haprobe.DbmMetadataClusterType {
	catalogMu.RLock()
	defer catalogMu.RUnlock()
	src := byDbType[dt]
	if len(src) == 0 {
		return nil
	}
	out := make([]haprobe.DbmMetadataClusterType, len(src))
	copy(out, src)
	return out
}

// RegisteredDbTypes returns all registered DbTypes (unordered).
func RegisteredDbTypes() []haprobe.DbType {
	catalogMu.RLock()
	defer catalogMu.RUnlock()
	out := make([]haprobe.DbType, 0, len(registeredTypes))
	for dt := range registeredTypes {
		out = append(out, dt)
	}
	return out
}

// ProviderOwnedDbTypes returns DbTypes registered by providers (unordered).
// Includes both pure provider types (e.g. redis) and types that took over a builtin
// placeholder.
func ProviderOwnedDbTypes() []haprobe.DbType {
	catalogMu.RLock()
	defer catalogMu.RUnlock()
	out := make([]haprobe.DbType, 0, len(providerTypes))
	for dt := range providerTypes {
		out = append(out, dt)
	}
	return out
}

// IsRegisteredClusterType reports whether the cluster type is in the catalog.
func IsRegisteredClusterType(ct haprobe.DbmMetadataClusterType) bool {
	catalogMu.RLock()
	defer catalogMu.RUnlock()
	_, ok := byClusterType[ct]
	return ok
}
