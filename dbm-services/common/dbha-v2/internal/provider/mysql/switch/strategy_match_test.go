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

package mysqlswitch

import (
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/failure"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// ============================================================
// 1. MatchProxyBackendSimultaneous tests
// ============================================================

func TestMatchProxyBackendSimultaneous_EmptyInstances(t *testing.T) {
	count := MatchProxyBackendSimultaneous(nil)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchProxyBackendSimultaneous_SingleClusterBothTypes(t *testing.T) {
	instances := []failure.Instance{
		{
			BkCloudID:   1,
			ClusterID:   100,
			ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeProxy,
		},
		{
			BkCloudID:    1,
			ClusterID:    100,
			ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
			MachineType:  haprobe.DbmMetadataMachineTypeBackend,
			InstanceRole: haprobe.MySQLStorageMaster,
		},
	}
	count := MatchProxyBackendSimultaneous(instances)
	if count != 1 {
		t.Errorf("expected 1, got %d", count)
	}
}

func TestMatchProxyBackendSimultaneous_SingleClusterOnlyProxy(t *testing.T) {
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
	}
	count := MatchProxyBackendSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchProxyBackendSimultaneous_SingleClusterOnlyBackend(t *testing.T) {
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
	}
	count := MatchProxyBackendSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchProxyBackendSimultaneous_BackendButNotMaster(t *testing.T) {
	// proxy + backend (but InstanceRole is not backend_master) => not matched
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageSlave},
	}
	count := MatchProxyBackendSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchProxyBackendSimultaneous_MultipleClustersPartialMatch(t *testing.T) {
	instances := []failure.Instance{
		// cluster 100: proxy + backend master => matched
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeBackend,
			InstanceRole: haprobe.MySQLStorageMaster},
		// cluster 200: only proxy => not matched
		{BkCloudID: 1, ClusterID: 200, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		// cluster 300: proxy + backend master => matched
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeBackend,
			InstanceRole: haprobe.MySQLStorageMaster},
	}
	count := MatchProxyBackendSimultaneous(instances)
	if count != 2 {
		t.Errorf("expected 2, got %d", count)
	}
}

func TestMatchProxyBackendSimultaneous_DifferentCloudsSameCluster(t *testing.T) {
	// different BkCloudID with same ClusterID should not be merged into the same cluster
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 2, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
	}
	count := MatchProxyBackendSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchProxyBackendSimultaneous_MultipleProxiesAndBackends(t *testing.T) {
	// multiple proxies and backends in the same cluster, count by cluster should be 1
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.1", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.2", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.3", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.4", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.5", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
	}
	count := MatchProxyBackendSimultaneous(instances)
	if count != 1 {
		t.Errorf("expected 1, got %d", count)
	}
}

// ============================================================
// 2. MatchSpiderRemoteMasterSimultaneous tests
// ============================================================

func TestMatchSpiderRemoteMasterSimultaneous_EmptyInstances(t *testing.T) {
	count := MatchSpiderRemoteMasterSimultaneous(nil)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_SingleClusterBothTypes(t *testing.T) {
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	count := MatchSpiderRemoteMasterSimultaneous(instances)
	if count != 1 {
		t.Errorf("expected 1, got %d", count)
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_SingleClusterOnlySpider(t *testing.T) {
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
	}
	count := MatchSpiderRemoteMasterSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_SingleClusterOnlyRemoteMaster(t *testing.T) {
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	count := MatchSpiderRemoteMasterSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_RemoteButNotMaster(t *testing.T) {
	// spider + remote (but InstanceRole is not remote_master) => not matched
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageSlave},
	}
	count := MatchSpiderRemoteMasterSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_MultipleClustersPartialMatch(t *testing.T) {
	instances := []failure.Instance{
		// cluster 100: spider + remote master => matched
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
		// cluster 200: only spider => not matched
		{BkCloudID: 1, ClusterID: 200, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		// cluster 300: spider + remote master => matched
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	count := MatchSpiderRemoteMasterSimultaneous(instances)
	if count != 2 {
		t.Errorf("expected 2, got %d", count)
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_DifferentCloudsSameCluster(t *testing.T) {
	// different BkCloudID with same ClusterID should not be merged into the same cluster
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 2, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	count := MatchSpiderRemoteMasterSimultaneous(instances)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_MultipleInstancesSameCluster(t *testing.T) {
	// multiple spiders and remote masters in the same cluster, count by cluster should be 1
	instances := []failure.Instance{
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.1", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.2", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.3", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.4", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	count := MatchSpiderRemoteMasterSimultaneous(instances)
	if count != 1 {
		t.Errorf("expected 1, got %d", count)
	}
}
