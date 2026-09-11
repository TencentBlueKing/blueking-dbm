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

import "dbm-services/common/dbha-v2/pkg/storage/haprobe"

// Built-in placeholder mappings (MySQL family + currently unsupported types).
// Providers may later take over any of these via Register; Redis is intentionally
// NOT registered here so it remains a pure-provider example.
func init() {
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeMySql,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeTendbha,
			haprobe.DbmMetadataClusterTypeTendbCluster,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeSqlServer,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeSqlServer,
			haprobe.DbmMetadataClusterTypeSqlServerSingle,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeMongo,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeMongoReplicaSet,
			haprobe.DbmMetadataClusterTypeMongoShardeCluster,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeRiak,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeRiak,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeHdfs,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeHdfs,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeEs,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeEs,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeKafka,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeKafka,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypeDoris,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypeDoris,
		},
	})
	registerBuiltin(Descriptor{
		DbType: haprobe.DbTypePulsar,
		ClusterTypes: []haprobe.DbmMetadataClusterType{
			haprobe.DbmMetadataClusterTypePulsar,
		},
	})
}
