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
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestNewScanSupportedDbTypes(t *testing.T) {
	tests := []struct {
		name  string
		types []haprobe.DbType
		want  []haprobe.DbType
	}{
		{
			name:  "mysql and redis",
			types: []haprobe.DbType{haprobe.DbTypeMySql, haprobe.DbTypeRedis},
			want:  []haprobe.DbType{haprobe.DbTypeMySql, haprobe.DbTypeRedis},
		},
		{
			name: "duplicates and invalid types are removed",
			types: []haprobe.DbType{
				haprobe.DbTypeMySql, haprobe.DbTypeMySql, haprobe.DbTypeNone, haprobe.DbTypeUnknown,
			},
			want: []haprobe.DbType{haprobe.DbTypeMySql},
		},
		{
			name:  "empty registry",
			types: nil,
			want:  nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := newScanSupportedDbTypes(tt.types)
			if len(got) != len(tt.want) {
				t.Fatalf("supported count = %d, want %d, got: %s", len(got), len(tt.want), formatDbTypeSet(got))
			}
			for _, dt := range tt.want {
				if _, ok := got[dt]; !ok {
					t.Errorf("missing db type %s in supported set", dt)
				}
			}
		})
	}
}

func TestFilterBySupportedDbTypesForScan(t *testing.T) {
	supported := newScanSupportedDbTypes([]haprobe.DbType{haprobe.DbTypeMySql})
	bizMeta := newBusinessMetadataForTest()

	filterBySupportedDbTypesForScan(1, bizMeta, supported)

	if len(bizMeta.MetaInsts) != 2 {
		t.Errorf("kept metas = %d, want 2", len(bizMeta.MetaInsts))
	}
	if len(bizMeta.Conds) != 2 {
		t.Errorf("kept conds = %d, want 2", len(bizMeta.Conds))
	}
	assertCondsMatchMeta(t, bizMeta)
	for _, meta := range bizMeta.MetaInsts {
		if _, ok := supported[meta.GetDbType()]; !ok {
			t.Errorf("unregistered db type kept: %s", meta.GetDbType())
		}
	}
}

func TestFilterBySupportedDbTypesForScan_EmptySetKeepsAll(t *testing.T) {
	bizMeta := newBusinessMetadataForTest()

	filterBySupportedDbTypesForScan(1, bizMeta, nil)

	if len(bizMeta.MetaInsts) != 4 || len(bizMeta.Conds) != 4 {
		t.Fatalf("fail-open violated, metas = %d, conds = %d", len(bizMeta.MetaInsts), len(bizMeta.Conds))
	}
	assertCondsMatchMeta(t, bizMeta)
}

func TestFilterBySupportedDbTypesForScan_AllUnsupported(t *testing.T) {
	bizMeta := newBusinessMetadataForTest()

	filterBySupportedDbTypesForScan(1, bizMeta,
		map[haprobe.DbType]struct{}{haprobe.DbTypeKafka: {}})

	if len(bizMeta.MetaInsts) != 0 || len(bizMeta.Conds) != 0 {
		t.Fatalf("all instances should be filtered, metas = %d, conds = %d",
			len(bizMeta.MetaInsts), len(bizMeta.Conds))
	}
}

func newBusinessMetadataForTest() *BusinessMetadata {
	instances := []struct {
		ip          string
		port        int
		clusterType haprobe.DbmMetadataClusterType
	}{
		{"127.0.0.1", 3306, haprobe.DbmMetadataClusterTypeTendbha},
		{"127.0.0.2", 3307, haprobe.DbmMetadataClusterTypeTendbCluster},
		{"127.0.0.3", 9200, haprobe.DbmMetadataClusterTypeEs},
		{"127.0.0.4", 9999, haprobe.DbmMetadataClusterType("unregistered.cluster")},
	}

	bizMeta := &BusinessMetadata{
		MetaInsts: make(map[string]*hamodel.DbmMetadata, len(instances)),
		Conds:     make([]*storage.DbInstance, 0, len(instances)),
	}
	for _, inst := range instances {
		meta := &hamodel.DbmMetadata{
			IP:          inst.ip,
			Port:        inst.port,
			ClusterType: inst.clusterType,
		}
		bizMeta.MetaInsts[instanceKey(meta.BkCloudID, meta.IP, meta.Port)] = meta
		bizMeta.Conds = append(bizMeta.Conds, &storage.DbInstance{
			BkCloudID: meta.BkCloudID,
			IP:        meta.IP,
			Port:      meta.Port,
		})
	}
	return bizMeta
}

func assertCondsMatchMeta(t *testing.T, bizMeta *BusinessMetadata) {
	t.Helper()
	if len(bizMeta.Conds) != len(bizMeta.MetaInsts) {
		t.Fatalf("conds = %d, metas = %d", len(bizMeta.Conds), len(bizMeta.MetaInsts))
	}
	for _, cond := range bizMeta.Conds {
		key := instanceKey(cond.BkCloudID, cond.IP, cond.Port)
		if _, ok := bizMeta.MetaInsts[key]; !ok {
			t.Errorf("cond %s has no metadata", key)
		}
	}
}
