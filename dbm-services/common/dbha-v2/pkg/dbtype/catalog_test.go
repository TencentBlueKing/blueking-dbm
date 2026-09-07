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

// All known DbmMetadataClusterType constants defined in haprobe.
// Completeness: each must either be registered or listed in unsupportedAllowlist.
var allKnownClusterTypes = []haprobe.DbmMetadataClusterType{
	haprobe.DbmMetadataClusterTypeTendbha,
	haprobe.DbmMetadataClusterTypeSqlServer,
	haprobe.DbmMetadataClusterTypeTendbCluster,
	haprobe.DbmMetadataClusterTypeSqlServerSingle,
	haprobe.DbmMetadataClusterTypeMongoReplicaSet,
	haprobe.DbmMetadataClusterTypeRiak,
	haprobe.DbmMetadataClusterTypeHdfs,
	haprobe.DbmMetadataClusterTypeTwemproxyRedis,
	haprobe.DbmMetadataClusterTypeRedis,
	haprobe.DbmMetadataClusterTypeEs,
	haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD,
	haprobe.DbmMetadataClusterTypeKafka,
	haprobe.DbmMetadataClusterTypeMongoShardeCluster,
	haprobe.DbmMetadataClusterTypeDoris,
	haprobe.DbmMetadataClusterTypePredixyTendisplusCluster,
	haprobe.DbmMetadataClusterTypePredixyRedisCluster,
	haprobe.DbmMetadataClusterTypePulsar,
}

// unsupportedAllowlist: cluster types that intentionally map to DbTypeNone.
// Currently empty; redis is provided by provider and tested separately.
var unsupportedAllowlist = map[haprobe.DbmMetadataClusterType]struct{}{}

// redisClusterTypes are owned by provider/redis/dbtypedesc and are NOT
// expected in the built-in catalog (pkg/dbtype alone).
var redisClusterTypes = map[haprobe.DbmMetadataClusterType]struct{}{
	haprobe.DbmMetadataClusterTypeTwemproxyRedis:           {},
	haprobe.DbmMetadataClusterTypeRedis:                    {},
	haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD:       {},
	haprobe.DbmMetadataClusterTypePredixyTendisplusCluster: {},
	haprobe.DbmMetadataClusterTypePredixyRedisCluster:      {},
}

func TestBuiltinCatalogCompleteness(t *testing.T) {
	for _, ct := range allKnownClusterTypes {
		if _, isRedis := redisClusterTypes[ct]; isRedis {
			if IsRegisteredClusterType(ct) {
				t.Errorf("redis cluster type %s must NOT be built-in; move to provider", ct)
			}
			continue
		}
		if _, allow := unsupportedAllowlist[ct]; allow {
			if IsRegisteredClusterType(ct) {
				t.Errorf("allowlisted unsupported type %s unexpectedly registered", ct)
			}
			continue
		}
		if !IsRegisteredClusterType(ct) {
			t.Errorf("cluster type %s is neither registered nor allowlisted", ct)
		}
	}
}

func TestBuiltinMySQLMapping(t *testing.T) {
	cases := []struct {
		ct   haprobe.DbmMetadataClusterType
		want haprobe.DbType
	}{
		{haprobe.DbmMetadataClusterTypeTendbha, haprobe.DbTypeMySql},
		{haprobe.DbmMetadataClusterTypeTendbCluster, haprobe.DbTypeMySql},
		{haprobe.DbmMetadataClusterTypeSqlServer, haprobe.DbTypeSqlServer},
		{haprobe.DbmMetadataClusterTypeMongoReplicaSet, haprobe.DbTypeMongo},
		{haprobe.DbmMetadataClusterTypeRiak, haprobe.DbTypeRiak},
		{haprobe.DbmMetadataClusterTypeHdfs, haprobe.DbTypeHdfs},
		{haprobe.DbmMetadataClusterTypeEs, haprobe.DbTypeEs},
		{haprobe.DbmMetadataClusterTypeKafka, haprobe.DbTypeKafka},
		{haprobe.DbmMetadataClusterTypeDoris, haprobe.DbTypeDoris},
		{haprobe.DbmMetadataClusterTypePulsar, haprobe.DbTypePulsar},
	}
	for _, tc := range cases {
		if got := DbTypeOf(tc.ct); got != tc.want {
			t.Errorf("DbTypeOf(%s) = %s, want %s", tc.ct, got, tc.want)
		}
	}
}

func TestUnknownClusterTypeMapsToNone(t *testing.T) {
	if got := DbTypeOf(haprobe.DbmMetadataClusterType("not-a-real-type")); got != haprobe.DbTypeNone {
		t.Errorf("unknown type mapped to %q, want empty DbTypeNone", got)
	}
}

func TestClusterTypesOfMySQL(t *testing.T) {
	cts := ClusterTypesOf(haprobe.DbTypeMySql)
	if len(cts) != 2 {
		t.Fatalf("ClusterTypesOf(mysql) len = %d, want 2", len(cts))
	}
}
