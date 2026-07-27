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
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestRegisterTakesOverBuiltinPlaceholder(t *testing.T) {
	t.Cleanup(snapshotForTest())

	// Takeover must keep the builtin kafka cluster type and may extend the set.
	Register(Descriptor{
		DbType: haprobe.DbTypeKafka,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeKafka,
		},
	})

	if got := DbTypeOf(haprobe.DbmMetadataClusterTypeKafka); got != haprobe.DbTypeKafka {
		t.Fatalf("DbTypeOf(kafka) = %q after takeover, want kafka", got)
	}
	owned := false
	for _, dt := range ProviderOwnedDbTypes() {
		if dt == haprobe.DbTypeKafka {
			owned = true
			break
		}
	}
	if !owned {
		t.Fatal("kafka missing from ProviderOwnedDbTypes after takeover")
	}
	catalogMu.RLock()
	_, stillBuiltin := builtinTypes[haprobe.DbTypeKafka]
	catalogMu.RUnlock()
	if stillBuiltin {
		t.Fatal("kafka still marked builtin after provider takeover")
	}
}

func TestRegisterDuplicateProviderPanics(t *testing.T) {
	t.Cleanup(snapshotForTest())

	Register(Descriptor{
		DbType: haprobe.DbTypeKafka,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeKafka,
		},
	})

	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic on second provider registration for kafka")
		}
	}()
	Register(Descriptor{
		DbType: haprobe.DbTypeKafka,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeKafka,
		},
	})
}

func TestRegisterTakeoverNarrowingPanics(t *testing.T) {
	t.Cleanup(snapshotForTest())

	// SqlServer has two cluster types; dropping one must panic without mutating state.
	before := ClusterTypesOf(haprobe.DbTypeSqlServer)
	if len(before) != 2 {
		t.Fatalf("precondition: sqlserver has %d cluster types, want 2", len(before))
	}

	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic when takeover narrows cluster type set")
		}
		after := ClusterTypesOf(haprobe.DbTypeSqlServer)
		if len(after) != 2 {
			t.Fatalf("registry mutated after failed takeover: got %v", after)
		}
		if DbTypeOf(haprobe.DbmMetadataClusterTypeSqlServer) != haprobe.DbTypeSqlServer {
			t.Fatal("sqlserver mapping lost after failed takeover")
		}
	}()
	Register(Descriptor{
		DbType: haprobe.DbTypeSqlServer,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeSqlServer,
			// missing SqlServerSingle — must panic
		},
	})
}

func TestRegisterTakeoverClearsOldMappings(t *testing.T) {
	t.Cleanup(snapshotForTest())

	// Simulate an extended takeover that keeps kafka and adds nothing else;
	// old mappings must still resolve and leftover keys must not remain under
	// the previous builtin-only set (already a single-element set for kafka).
	Register(Descriptor{
		DbType: haprobe.DbTypeKafka,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeKafka,
		},
	})
	cts := ClusterTypesOf(haprobe.DbTypeKafka)
	if len(cts) != 1 || cts[0] != haprobe.DbmMetadataClusterTypeKafka {
		t.Fatalf("unexpected cluster types after takeover: %v", cts)
	}
}
