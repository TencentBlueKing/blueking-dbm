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

package failure

import (
	"slices"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// registerNonSwitchableOnce registers the matcher when the db type has no matcher yet.
// The registry is process-wide, so registering the same db type twice panics.
func registerNonSwitchableOnce(dbType haprobe.DbType, matcher NonSwitchableMatcher) {
	if slices.Contains(RegisteredNonSwitchableDbTypes(), dbType) {
		return
	}
	RegisterNonSwitchableMatcher(dbType, matcher)
}

// registerRedisNonSwitchable registers the redis matcher: the storage layer of the
// cluster-protocol clusters never triggers a switch.
func registerRedisNonSwitchable() {
	registerNonSwitchableOnce(haprobe.DbTypeRedis, func(inst *Instance) bool {
		return inst.ClusterType == haprobe.DbmMetadataClusterTypePredixyRedisCluster &&
			inst.MachineType != haprobe.DbmMetadataMachineTypePredixy
	})
}

func TestNonSwitchableOfUsesTheRegisteredMatcher(t *testing.T) {
	registerRedisNonSwitchable()

	cases := []struct {
		name     string
		inst     *Instance
		expected bool
	}{
		{
			name: "redis cluster-protocol storage",
			inst: &Instance{
				DbType:      haprobe.DbTypeRedis,
				ClusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
				MachineType: haprobe.DbmMetadataMachineTypeTendisCache,
			},
			expected: true,
		},
		{
			name: "redis cluster-protocol proxy",
			inst: &Instance{
				DbType:      haprobe.DbTypeRedis,
				ClusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
				MachineType: haprobe.DbmMetadataMachineTypePredixy,
			},
			expected: false,
		},
		{
			name: "redis instance of another cluster type",
			inst: &Instance{
				DbType:      haprobe.DbTypeRedis,
				ClusterType: haprobe.DbmMetadataClusterTypeRedis,
				MachineType: haprobe.DbmMetadataMachineTypeTendisCache,
			},
			expected: false,
		},
		{
			name: "instance of an unregistered db type",
			inst: &Instance{
				DbType:      haprobe.DbTypeMySql,
				ClusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
				MachineType: haprobe.DbmMetadataMachineTypeTendisCache,
			},
			expected: false,
		},
		{
			name:     "nil instance",
			inst:     nil,
			expected: false,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := NonSwitchableOf(tc.inst); got != tc.expected {
				t.Fatalf("NonSwitchableOf() = %v, want %v", got, tc.expected)
			}
		})
	}
}

func TestRegisteredNonSwitchableDbTypesContainsRegisteredType(t *testing.T) {
	registerRedisNonSwitchable()
	registerNonSwitchableOnce(haprobe.DbTypeMySql, func(inst *Instance) bool {
		return false
	})

	registered := RegisteredNonSwitchableDbTypes()
	for _, dbType := range []haprobe.DbType{haprobe.DbTypeRedis, haprobe.DbTypeMySql} {
		if !slices.Contains(registered, dbType) {
			t.Fatalf("RegisteredNonSwitchableDbTypes() = %v, want to contain %s", registered, dbType)
		}
	}
}

func TestRegisterNonSwitchableMatcherDuplicatePanics(t *testing.T) {
	registerRedisNonSwitchable()

	defer func() {
		if recovered := recover(); recovered == nil {
			t.Fatal("expected a panic on duplicate non-switchable registration")
		}
	}()

	RegisterNonSwitchableMatcher(haprobe.DbTypeRedis, func(inst *Instance) bool {
		return true
	})
}

func TestRegisterNonSwitchableMatcherInvalidDbTypePanics(t *testing.T) {
	defer func() {
		if recovered := recover(); recovered == nil {
			t.Fatal("expected a panic on invalid DbType")
		}
	}()

	RegisterNonSwitchableMatcher(haprobe.DbTypeNone, func(inst *Instance) bool {
		return true
	})
}

func TestRegisterNonSwitchableMatcherNilMatcherPanics(t *testing.T) {
	defer func() {
		if recovered := recover(); recovered == nil {
			t.Fatal("expected a panic on nil matcher")
		}
	}()

	RegisterNonSwitchableMatcher(haprobe.DbTypeMySql, nil)
}
