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

// Package dbcred resolves per-instance probe credentials.
//
// It is the generic seam between admin, which needs credentials while
// generating a probe config, and each DB resolver, which knows how to fetch
// them. Admin never imports a concrete resolver.
package dbcred

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Instance identifies one DB instance whose credential is needed.
// BkCloudID is not a field: a Fill batch always covers one cloud area, so it is
// passed once as a Fill argument.
type Instance struct {
	ClusterID    int
	ClusterType  haprobe.DbmMetadataClusterType
	MachineType  haprobe.DbmMetadataMachineType
	InstanceRole haprobe.DbmMetadataInstanceRole
	AccessLayer  haprobe.DbmMetadataAccessLayerType
	IP           string
	Port         int
}

// Item pairs an instance with the credential slot the resolver fills in.
type Item struct {
	Instance Instance
	// User / Password are OUTPUTS, filled by Resolver.Fill.
	// A zero value means "no credential resolved" and is a legitimate outcome.
	User     string
	Password string
}

// Resolver resolves credentials of one DB type.
type Resolver interface {
	// Fill resolves credentials for a batch of instances of one cloud area.
	//
	// Fill is the rate-limit seam: every instance of one machine arrives in a
	// single call, so implementations must batch their remote lookups instead
	// of querying per instance.
	//
	// Implementations must never substitute a placeholder password: an
	// instance whose credential cannot be resolved keeps its zero value, so
	// admin can report it and the probe falls through to the liveness
	// double-check.
	Fill(ctx context.Context, bkCloudID int, items []*Item) error
}

// DbmApi mirrors one DBM API entry of the host configuration. It has the same
// shape as admin's / analysis's existing DbmApi entry, so a resolver receives
// exactly what it needs without either side importing the other.
//
// Method is carried for parity with the host config, but the password client
// currently hardcodes POST; it is not read by any Fill implementation yet.
type DbmApi struct {
	Api     string
	Token   string
	Method  string
	Timeout time.Duration
}

// ConfigLookup resolves a named DBM API entry from the HOST's configuration.
//
// The host (admin) supplies the closure; each resolver asks for the entries it
// needs BY NAME. The host never knows which names exist, so adding a DB type
// never requires an admin code change - only a config entry.
type ConfigLookup func(name string) (DbmApi, bool)

// Configurer is OPTIONAL.
//
// A resolver needing host configuration (e.g. a password-service endpoint)
// implements it; one that resolves credentials locally simply does not, and is
// skipped by ConfigureAll. This is how "needs an API" and "needs nothing"
// coexist without admin knowing the difference.
//
// Implementations must not call back into this package (Register / Lookup /
// ConfigureAll): ConfigureAll holds the registry write lock while invoking
// Configure, so such a call would deadlock.
type Configurer interface {
	Configure(lookup ConfigLookup) error
}

var (
	mu           sync.RWMutex
	registry     = map[haprobe.DbType]Resolver{}
	unconfigured = map[haprobe.DbType]struct{}{}
)

// Register registers a credential resolver for a DbType. Panics on invalid or
// duplicate registration.
func Register(dt haprobe.DbType, p Resolver) {
	if dt == haprobe.DbTypeNone || dt == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("dbcred: refuse to register invalid DbType: %q", dt))
	}
	if p == nil {
		panic(fmt.Sprintf("dbcred: refuse to register nil resolver for DbType: %s", dt))
	}

	mu.Lock()
	defer mu.Unlock()

	if _, exists := registry[dt]; exists {
		panic(fmt.Sprintf("dbcred: duplicate DbType registration: %s", dt))
	}
	registry[dt] = p
}

// Lookup returns the resolver registered for dt.
func Lookup(dt haprobe.DbType) (Resolver, bool) {
	mu.RLock()
	defer mu.RUnlock()

	p, ok := registry[dt]
	return p, ok
}

// RegisteredDbTypes returns all registered DbTypes, sorted, for startup self-check.
func RegisteredDbTypes() []haprobe.DbType {
	mu.RLock()
	defer mu.RUnlock()

	out := make([]haprobe.DbType, 0, len(registry))
	for dt := range registry {
		out = append(out, dt)
	}
	sort.Slice(out, func(i, j int) bool { return string(out[i]) < string(out[j]) })
	return out
}

// ConfigureAll hands the lookup closure to every registered resolver that
// implements Configurer; the rest are skipped.
//
// A resolver failing to configure is reported and recorded, but startup
// continues ("Warn continue"). The resolver stays registered, and its Fill
// then fails per instance - yielding an empty password that falls through to
// the liveness double-check rather than blocking the whole binary.
func ConfigureAll(lookup ConfigLookup) {
	mu.Lock()
	defer mu.Unlock()

	for dt, p := range registry {
		c, ok := p.(Configurer)
		if !ok {
			continue
		}
		if err := c.Configure(lookup); err != nil {
			logger.Warn("configure credential resolver failed, db_type: %s, errmsg: %s", dt, err)
			unconfigured[dt] = struct{}{}
			continue
		}
		// A previously failed resolver that now configures must leave the set,
		// otherwise a config reload would keep reporting it forever.
		delete(unconfigured, dt)
	}
}

// UnconfiguredDbTypes returns DbTypes whose resolver failed to configure, for
// the startup self-check log.
func UnconfiguredDbTypes() []haprobe.DbType {
	mu.RLock()
	defer mu.RUnlock()

	out := make([]haprobe.DbType, 0, len(unconfigured))
	for dt := range unconfigured {
		out = append(out, dt)
	}
	sort.Slice(out, func(i, j int) bool { return string(out[i]) < string(out[j]) })
	return out
}
