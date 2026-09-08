/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package task

import (
	"errors"
	"testing"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
)

func restoreHostCheckDeps(t *testing.T) {
	t.Helper()
	t.Cleanup(func() {
		fetchSwitchesFn = dbmapi.GetDissolvedUworkInfo
		checkDissolvedFn = dbmapi.CheckHostIsDissolved
		checkUworkFn = dbmapi.CheckHostHasUwork
		resourceDeleteFn = dbmapi.ResourceDelete
		listUnusedMachinesFn = listUnusedMachines
		markUnusedHostsFn = markUnusedHosts
	})
}

func sampleUnused() []model.TbRpDetail {
	return []model.TbRpDetail{
		{BkHostID: 1001, IP: "127.0.0.1", BkCloudID: 0, Status: model.Unused},
		{BkHostID: 1002, IP: "127.0.0.2", BkCloudID: 0, Status: model.Unused},
	}
}

func TestDissolveHostCheckSwitchOffSkipsInspect(t *testing.T) {
	restoreHostCheckDeps(t)
	listed := false
	marked := false
	deleted := false
	fetchSwitchesFn = func() (dbmapi.DissolvedUworkInfo, error) {
		return dbmapi.DissolvedUworkInfo{HostDissolvedSwitch: false, HostToFaultSwitch: true}, nil
	}
	listUnusedMachinesFn = func() ([]model.TbRpDetail, error) {
		listed = true
		return sampleUnused(), nil
	}
	markUnusedHostsFn = func(hostIds []int, status string) error {
		marked = true
		return nil
	}
	resourceDeleteFn = func(hosts []dbmapi.ResourceDeleteHost, event, remark string) error {
		deleted = true
		return nil
	}

	if err := DissolveHostCheck(); err != nil {
		t.Fatalf("DissolveHostCheck() err=%v", err)
	}
	if listed || marked || deleted {
		t.Fatal("HOST_DISSOLVED_SWITCH off must skip dissolve inspect")
	}
}

func TestDissolveHostCheckSwitchAPIErrorSkipsInspect(t *testing.T) {
	restoreHostCheckDeps(t)
	listed := false
	fetchSwitchesFn = func() (dbmapi.DissolvedUworkInfo, error) {
		return dbmapi.DissolvedUworkInfo{}, errors.New("switch api down")
	}
	listUnusedMachinesFn = func() ([]model.TbRpDetail, error) {
		listed = true
		return sampleUnused(), nil
	}

	if err := DissolveHostCheck(); err == nil {
		t.Fatal("expected switch api error")
	}
	if listed {
		t.Fatal("switch api error must not start dissolve inspect")
	}
}

func TestDissolveHostCheckMarkThenDelete(t *testing.T) {
	restoreHostCheckDeps(t)
	var markedStatus string
	var markedIds []int
	var deletedEvent string
	var deletedHosts []dbmapi.ResourceDeleteHost

	fetchSwitchesFn = func() (dbmapi.DissolvedUworkInfo, error) {
		return dbmapi.DissolvedUworkInfo{HostDissolvedSwitch: true}, nil
	}
	listUnusedMachinesFn = func() ([]model.TbRpDetail, error) { return sampleUnused(), nil }
	checkDissolvedFn = func(ids []int) ([]int, error) { return []int{1002}, nil }
	markUnusedHostsFn = func(hostIds []int, status string) error {
		markedIds = append([]int{}, hostIds...)
		markedStatus = status
		return nil
	}
	resourceDeleteFn = func(hosts []dbmapi.ResourceDeleteHost, event, remark string) error {
		if markedStatus == "" {
			t.Fatal("resource delete called before status update")
		}
		deletedEvent = event
		deletedHosts = hosts
		return nil
	}

	if err := DissolveHostCheck(); err != nil {
		t.Fatalf("DissolveHostCheck() err=%v", err)
	}
	if markedStatus != model.Dissolved || len(markedIds) != 1 || markedIds[0] != 1002 {
		t.Fatalf("mark unused: status=%s ids=%v", markedStatus, markedIds)
	}
	if deletedEvent != dbmapi.EventToRecycle || len(deletedHosts) != 1 || deletedHosts[0].BkHostID != 1002 {
		t.Fatalf("delete: event=%s hosts=%+v", deletedEvent, deletedHosts)
	}
}

func TestDissolveHostCheckDeleteFailKeepsMarked(t *testing.T) {
	restoreHostCheckDeps(t)
	marked := false
	fetchSwitchesFn = func() (dbmapi.DissolvedUworkInfo, error) {
		return dbmapi.DissolvedUworkInfo{HostDissolvedSwitch: true}, nil
	}
	listUnusedMachinesFn = func() ([]model.TbRpDetail, error) { return sampleUnused(), nil }
	checkDissolvedFn = func(ids []int) ([]int, error) { return []int{1001}, nil }
	markUnusedHostsFn = func(hostIds []int, status string) error {
		if status != model.Dissolved {
			t.Fatalf("status=%s", status)
		}
		marked = true
		return nil
	}
	resourceDeleteFn = func(hosts []dbmapi.ResourceDeleteHost, event, remark string) error {
		return errors.New("delete failed")
	}

	if err := DissolveHostCheck(); err == nil {
		t.Fatal("expected delete error")
	}
	if !marked {
		t.Fatal("status must be marked even if resource_delete fails")
	}
}

func TestFaultHostCheckSwitchOffStillMarks(t *testing.T) {
	restoreHostCheckDeps(t)
	marked := false
	deleted := false
	fetchSwitchesFn = func() (dbmapi.DissolvedUworkInfo, error) {
		return dbmapi.DissolvedUworkInfo{HostDissolvedSwitch: true, HostToFaultSwitch: false}, nil
	}
	listUnusedMachinesFn = func() ([]model.TbRpDetail, error) { return sampleUnused(), nil }
	checkUworkFn = func(ids []int) ([]dbmapi.UworkFaultHost, error) {
		return []dbmapi.UworkFaultHost{{BkHostID: 1001, HasOpenTickets: true}}, nil
	}
	markUnusedHostsFn = func(hostIds []int, status string) error {
		marked = true
		if status != model.FaultHazard {
			t.Fatalf("status=%s", status)
		}
		return nil
	}
	resourceDeleteFn = func(hosts []dbmapi.ResourceDeleteHost, event, remark string) error {
		deleted = true
		return nil
	}

	if err := FaultHostCheck(); err != nil {
		t.Fatalf("FaultHostCheck() err=%v", err)
	}
	if !marked {
		t.Fatal("switch off must still mark FaultHazard")
	}
	if deleted {
		t.Fatal("HOST_TO_FAULT_SWITCH off must not call resource_delete")
	}
}

func TestFaultHostCheckMarkThenDelete(t *testing.T) {
	restoreHostCheckDeps(t)
	var markedStatus string
	fetchSwitchesFn = func() (dbmapi.DissolvedUworkInfo, error) {
		return dbmapi.DissolvedUworkInfo{HostToFaultSwitch: true}, nil
	}
	listUnusedMachinesFn = func() ([]model.TbRpDetail, error) { return sampleUnused(), nil }
	checkUworkFn = func(ids []int) ([]dbmapi.UworkFaultHost, error) {
		return []dbmapi.UworkFaultHost{{BkHostID: 1001, HasOpenTickets: true}}, nil
	}
	markUnusedHostsFn = func(hostIds []int, status string) error {
		markedStatus = status
		return nil
	}
	var deletedEvent string
	resourceDeleteFn = func(hosts []dbmapi.ResourceDeleteHost, event, remark string) error {
		if markedStatus == "" {
			t.Fatal("resource delete called before status update")
		}
		deletedEvent = event
		return nil
	}

	if err := FaultHostCheck(); err != nil {
		t.Fatalf("FaultHostCheck() err=%v", err)
	}
	if markedStatus != model.FaultHazard {
		t.Fatalf("status=%s", markedStatus)
	}
	if deletedEvent != dbmapi.EventToFault {
		t.Fatalf("event=%s", deletedEvent)
	}
}

func TestFilterUnusedHitsSkipsAlreadyTransferred(t *testing.T) {
	machines := []model.TbRpDetail{{BkHostID: 1001}}
	got := filterUnusedHits(machines, []int{1001, 1002, 1001})
	if len(got) != 1 || got[0] != 1001 {
		t.Fatalf("got=%v", got)
	}
}
