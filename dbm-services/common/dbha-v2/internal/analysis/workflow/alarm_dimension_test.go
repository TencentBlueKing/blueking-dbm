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

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// TestFillSwitchV1DimensionsOmitsNewMaster asserts fillSwitchV1Dimensions copies instance
// metadata into switch v1 dimensions and leaves new-master fields unset.
func TestFillSwitchV1DimensionsOmitsNewMaster(t *testing.T) {
	const switchID = "switch-001"

	inst := &dbm.DbInstMetadata{
		BkCloudID:    1,
		IP:           "127.0.0.1",
		Port:         3306,
		BkBizID:      2,
		Cluster:      "db.local",
		MachineType:  haprobe.DbmMetadataMachineTypeBackend,
		InstanceRole: haprobe.MySQLStorageMaster,
		BkIdcCityID:  3,
		Status:       dbm.Running,
	}
	event := &monitor.EventData{Name: string(haprobe.DbEventNameMysqlSwitchFailureV1)}

	fillSwitchV1Dimensions(event, inst, switchID)

	if event.Dimension.SwitchInfoServerIpV1 != "127.0.0.1" {
		t.Fatalf("server_ip: %s", event.Dimension.SwitchInfoServerIpV1)
	}
	if event.Dimension.SwitchInfoServerPortV1 != 3306 {
		t.Fatalf("server_port: %d", event.Dimension.SwitchInfoServerPortV1)
	}
	if event.Dimension.SwitchInfoBkBizIdV1 != "2" {
		t.Fatalf("appid: %s", event.Dimension.SwitchInfoBkBizIdV1)
	}
	if event.Dimension.SwitchInfoClusterDomainV1 != "db.local" {
		t.Fatalf("cluster_domain: %s", event.Dimension.SwitchInfoClusterDomainV1)
	}
	if event.Dimension.SwitchInfoMachineTypeV1 != string(haprobe.DbmMetadataMachineTypeBackend) {
		t.Fatalf("machine_type: %s", event.Dimension.SwitchInfoMachineTypeV1)
	}
	if event.Dimension.SwitchInfoInstanceRoleV1 != string(haprobe.MySQLStorageMaster) {
		t.Fatalf("instance_role: %s", event.Dimension.SwitchInfoInstanceRoleV1)
	}
	if event.Dimension.SwitchInfoIdcV1 != "3" {
		t.Fatalf("idc: %s", event.Dimension.SwitchInfoIdcV1)
	}
	if event.Dimension.SwitchInfoStatusV1 != string(dbm.Running) {
		t.Fatalf("status: %s", event.Dimension.SwitchInfoStatusV1)
	}
	wantCheckID := generateDoubleCheckID(switchID, inst.BkCloudID, inst.IP)
	if event.Dimension.SwitchInfoCheckIdV1 != wantCheckID {
		t.Fatalf("double_check_id: %d", event.Dimension.SwitchInfoCheckIdV1)
	}
	if event.Dimension.SwitchInfoNewMasterHost != "" || event.Dimension.SwitchInfoNewMasterPort != 0 ||
		event.Dimension.SwitchInfoNewMasterBinlogFile != "" || event.Dimension.SwitchInfoNewMasterBinlogPos != 0 {
		t.Fatal("new master dimensions must stay unset")
	}
}

// TestFillDetectV1DimensionsForDoubleCheckSSH asserts fillDetectV1Dimensions fills
// detect v1 dimensions for a double-check SSH failure, sets SSH-failed status, and
// leaves idc empty.
func TestFillDetectV1DimensionsForDoubleCheckSSH(t *testing.T) {
	meta := &hamodel.DbmMetadata{
		BkCloudID:    4,
		IP:           "127.0.0.1",
		Port:         3306,
		BkBizID:      5,
		Cluster:      "db.local",
		MachineType:  haprobe.DbmMetadataMachineTypeBackend,
		ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
		InstanceRole: haprobe.MySQLStorageMaster,
		BkIdcCityID:  9,
		Status:       "running",
	}
	event := &monitor.EventData{Name: haprobe.DbEventNameDoubleCheckSshFailureV1.String()}

	fillDetectV1Dimensions(event, meta)

	if event.Dimension.BkCloudId != 4 {
		t.Fatalf("bk_cloud_id: %d", event.Dimension.BkCloudId)
	}
	if event.Dimension.SwitchInfoBkBizIdV1 != "5" {
		t.Fatalf("appid: %s", event.Dimension.SwitchInfoBkBizIdV1)
	}
	if event.Dimension.SwitchInfoServerIpV1 != "127.0.0.1" || event.Dimension.SwitchInfoServerPortV1 != 3306 {
		t.Fatalf("server: %s:%d", event.Dimension.SwitchInfoServerIpV1, event.Dimension.SwitchInfoServerPortV1)
	}
	if event.Dimension.SwitchInfoClusterDomainV1 != "db.local" {
		t.Fatalf("cluster_domain: %s", event.Dimension.SwitchInfoClusterDomainV1)
	}
	if event.Dimension.SwitchInfoMachineTypeV1 != string(haprobe.DbmMetadataMachineTypeBackend) {
		t.Fatalf("machine_type: %s", event.Dimension.SwitchInfoMachineTypeV1)
	}
	if event.Dimension.SwitchInfoDetectClusterType != string(haprobe.DbmMetadataClusterTypeTendbha) {
		t.Fatalf("cluster_type: %s", event.Dimension.SwitchInfoDetectClusterType)
	}
	if event.Dimension.SwitchInfoInstanceRoleV1 != string(haprobe.MySQLStorageMaster) {
		t.Fatalf("instance_role: %s", event.Dimension.SwitchInfoInstanceRoleV1)
	}
	if event.Dimension.SwitchInfoStatusV1 != sshCheckFailedStatus {
		t.Fatalf("status: %s", event.Dimension.SwitchInfoStatusV1)
	}
	if event.Dimension.SwitchInfoIdcV1 != "" {
		t.Fatalf("idc: %s", event.Dimension.SwitchInfoIdcV1)
	}
}

// TestFillDetectV1DimensionsSkipsSSHStatusForOtherEvents asserts fillDetectV1Dimensions
// leaves SSH status empty for events other than double-check SSH failure, while still
// filling bk_cloud_id and leaving idc empty.
func TestFillDetectV1DimensionsSkipsSSHStatusForOtherEvents(t *testing.T) {
	meta := &hamodel.DbmMetadata{
		BkCloudID: 4,
		IP:        "127.0.0.1",
		Port:      3306,
		BkBizID:   5,
	}
	event := &monitor.EventData{Name: haprobe.DbEventNameSshAuthFailure.String()}

	fillDetectV1Dimensions(event, meta)

	if event.Dimension.SwitchInfoStatusV1 != "" {
		t.Fatalf("status: %s", event.Dimension.SwitchInfoStatusV1)
	}
	if event.Dimension.BkCloudId != 4 {
		t.Fatalf("bk_cloud_id: %d", event.Dimension.BkCloudId)
	}
	if event.Dimension.SwitchInfoIdcV1 != "" {
		t.Fatalf("idc: %s", event.Dimension.SwitchInfoIdcV1)
	}
}
