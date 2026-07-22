/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package manage

import (
	"encoding/json"
	"testing"

	"dbm-services/common/db-resource/internal/model"
)

func mustLabels(t *testing.T, labels []string) json.RawMessage {
	t.Helper()
	if labels == nil {
		return json.RawMessage("[]")
	}
	b, err := json.Marshal(labels)
	if err != nil {
		t.Fatalf("marshal labels: %v", err)
	}
	return b
}

func host(t *testing.T, id int, ip, asset string, biz int, rsType string, labels []string) model.TbRpDetail {
	t.Helper()
	return model.TbRpDetail{
		BkHostID:          id,
		IP:                ip,
		BkSvrOwnerAssetID: asset,
		DedicatedBiz:      biz,
		RsType:            rsType,
		Labels:            mustLabels(t, labels),
		Status:            model.Unused,
	}
}

func TestSameSvrOwner_EmptyAsset_Zero(t *testing.T) {
	cur := host(t, 1, "127.0.0.1", "", 100, model.RESOURCE_TYPE_PUBLIC, nil)
	pool := []model.TbRpDetail{cur, host(t, 2, "127.0.0.2", "M1", 100, model.RESOURCE_TYPE_PUBLIC, nil)}
	if n := SameSvrOwnerCount(cur, pool); n != 0 {
		t.Fatalf("want 0, got %d", n)
	}
}

func TestSameSvrOwner_AE1_PublicAndDedicatedNoLabel(t *testing.T) {
	// AE1: 专属 B 无标签 + 公共池无标签同母机 → 2
	a := host(t, 1, "127.0.0.1", "M1", 100, model.RESOURCE_TYPE_PUBLIC, nil)
	b := host(t, 2, "127.0.0.2", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil)
	c := host(t, 3, "127.0.0.3", "M2", 100, model.RESOURCE_TYPE_PUBLIC, nil) // 其他母机
	pool := []model.TbRpDetail{a, b, c}
	peers := ListSameSvrOwnerPeers(a, pool)
	if len(peers) != 2 {
		t.Fatalf("want 2 peers, got %d", len(peers))
	}
	ips := PeerIPsFromHosts(peers)
	if len(ips) != 2 || ips[0] != "127.0.0.1" || ips[1] != "127.0.0.2" {
		t.Fatalf("unexpected ips: %v", ips)
	}
}

func TestSameSvrOwner_AE2_LabeledExcludesPublic(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "M1", 100, "mysql", []string{"t1"})
	pub := host(t, 2, "127.0.0.2", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil)
	sameBizTag := host(t, 3, "127.0.0.3", "M1", 100, "mysql", []string{"t1", "t9"})
	sameBizOtherTag := host(t, 4, "127.0.0.4", "M1", 100, "mysql", []string{"t2"})
	pool := []model.TbRpDetail{a, pub, sameBizTag, sameBizOtherTag}
	peers := ListSameSvrOwnerPeers(a, pool)
	if len(peers) != 2 {
		t.Fatalf("want 2 (self+t1), got %d", len(peers))
	}
	ips := PeerIPsFromHosts(peers)
	want := map[string]bool{"127.0.0.1": true, "127.0.0.3": true}
	for _, ip := range ips {
		if !want[ip] {
			t.Fatalf("unexpected ip %s in %v", ip, ips)
		}
	}
}

func TestSameSvrOwner_RsType_DedicatedAllowsPublic(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "M1", 100, "mysql", nil)
	pub := host(t, 2, "127.0.0.2", "M1", 100, model.RESOURCE_TYPE_PUBLIC, nil)
	redis := host(t, 3, "127.0.0.3", "M1", 100, "redis", nil)
	pool := []model.TbRpDetail{a, pub, redis}
	if n := SameSvrOwnerCount(a, pool); n != 2 {
		t.Fatalf("want 2 (self+public), got %d", n)
	}
}

func TestSameSvrOwner_RsType_PublicUnlimited(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil)
	mysql := host(t, 2, "127.0.0.2", "M1", 0, "mysql", nil)
	redis := host(t, 3, "127.0.0.3", "M1", 200, "redis", nil)
	pool := []model.TbRpDetail{a, mysql, redis}
	// 当前公共池无标签：同伴无标签即可，业务不限；rs_type 不限
	if n := SameSvrOwnerCount(a, pool); n != 3 {
		t.Fatalf("want 3, got %d", n)
	}
}

func TestSameSvrOwner_OnlySelf(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "M1", 100, "mysql", nil)
	if n := SameSvrOwnerCount(a, []model.TbRpDetail{a}); n != 1 {
		t.Fatalf("want 1, got %d", n)
	}
}

func TestSameSvrOwner_NoLabel_ExcludesOtherDedicated(t *testing.T) {
	// 专属 B 无标签：同伴须无标签，且专属为公共或 B；其他专属业务 C 不计入
	a := host(t, 1, "127.0.0.1", "M1", 100, "mysql", nil)
	pub := host(t, 2, "127.0.0.2", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil)
	otherBiz := host(t, 3, "127.0.0.3", "M1", 200, "mysql", nil)
	pool := []model.TbRpDetail{a, pub, otherBiz}
	peers := ListSameSvrOwnerPeers(a, pool)
	if len(peers) != 2 {
		t.Fatalf("want 2 (self+public), got %d", len(peers))
	}
}

func TestFillSameSvrOwnerCounts_Grouped(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "M1", 100, model.RESOURCE_TYPE_PUBLIC, nil)
	b := host(t, 2, "127.0.0.2", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil)
	details := []model.TbRpDetail{a, b}
	byAsset := GroupBySvrOwnerAsset([]model.TbRpDetail{a, b})
	FillSameSvrOwnerCounts(details, byAsset)
	if details[0].SameSvrOwnerCount != 2 || details[1].SameSvrOwnerCount != 2 {
		t.Fatalf("counts=%d,%d", details[0].SameSvrOwnerCount, details[1].SameSvrOwnerCount)
	}
}

func TestCollectSvrOwnerAssetIDs(t *testing.T) {
	hosts := []model.TbRpDetail{
		host(t, 1, "127.0.0.1", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil),
		host(t, 2, "127.0.0.2", "", 0, model.RESOURCE_TYPE_PUBLIC, nil),
		host(t, 3, "127.0.0.3", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil),
		host(t, 4, "127.0.0.4", "M2", 0, model.RESOURCE_TYPE_PUBLIC, nil),
	}
	ids := CollectSvrOwnerAssetIDs(hosts)
	if len(ids) != 2 {
		t.Fatalf("want 2 unique assets, got %v", ids)
	}
}
