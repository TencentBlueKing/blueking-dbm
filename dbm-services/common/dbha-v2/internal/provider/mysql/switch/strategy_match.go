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
	"dbm-services/common/dbha-v2/internal/analysis/failure"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// MatchProxyBackendSimultaneous matches cases where proxy and backend master fail simultaneously
// within the same cluster (BkCloudID:ClusterID).
// A backend master must satisfy both MachineType == backend and InstanceRole == MySQLStorageMaster.
// Returns the count of matched clusters.
func MatchProxyBackendSimultaneous(instances []failure.Instance) int {
	// sub-group by BkCloudID:ClusterID, reusing switchcore.GenerateClusterKey
	clusterGroups := make(map[switchcore.ClusterKey][]failure.Instance)
	for _, inst := range instances {
		key := switchcore.GenerateClusterKey(inst.BkCloudID, inst.ClusterID)
		clusterGroups[key] = append(clusterGroups[key], inst)
	}

	count := 0
	for _, group := range clusterGroups {
		hasProxy := false
		hasBackendMaster := false
		for _, inst := range group {
			if inst.ClusterType != haprobe.DbmMetadataClusterTypeTendbha {
				continue
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeProxy {
				hasProxy = true
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeBackend &&
				inst.InstanceRole == haprobe.MySQLStorageMaster {
				hasBackendMaster = true
			}
			if hasProxy && hasBackendMaster {
				break
			}
		}
		if hasProxy && hasBackendMaster {
			count++
		}
	}

	return count
}

// MatchSpiderRemoteMasterSimultaneous matches cases where spider and remote master fail simultaneously
// within the same cluster (BkCloudID:ClusterID).
// A remote master must satisfy both MachineType == remote and InstanceRole == TenDBClusterStorageMaster.
// Returns the count of matched clusters.
func MatchSpiderRemoteMasterSimultaneous(instances []failure.Instance) int {
	// sub-group by BkCloudID:ClusterID, reusing switchcore.GenerateClusterKey
	clusterGroups := make(map[switchcore.ClusterKey][]failure.Instance)
	for _, inst := range instances {
		key := switchcore.GenerateClusterKey(inst.BkCloudID, inst.ClusterID)
		clusterGroups[key] = append(clusterGroups[key], inst)
	}

	count := 0
	for _, group := range clusterGroups {
		hasSpider := false
		hasRemoteMaster := false
		for _, inst := range group {
			if inst.ClusterType != haprobe.DbmMetadataClusterTypeTendbCluster {
				continue
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeSpider {
				hasSpider = true
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeRemote &&
				inst.InstanceRole == haprobe.TenDBClusterStorageMaster {
				hasRemoteMaster = true
			}
			if hasSpider && hasRemoteMaster {
				break
			}
		}
		if hasSpider && hasRemoteMaster {
			count++
		}
	}

	return count
}
