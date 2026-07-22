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
	"testing"

	"dbm-services/common/db-resource/internal/model"
)

// Covers AE6: IP 接口 count 与可复制 ips 长度一致（去空/去重后）。
func TestSameSvrOwnerIPs_MatchesCount(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "M1", 100, model.RESOURCE_TYPE_PUBLIC, nil)
	b := host(t, 2, "127.0.0.2", "M1", 0, model.RESOURCE_TYPE_PUBLIC, nil)
	excluded := host(t, 3, "127.0.0.3", "M1", 100, model.RESOURCE_TYPE_PUBLIC, []string{"t1"})
	pool := []model.TbRpDetail{a, b, excluded}
	peers := ListSameSvrOwnerPeers(a, pool)
	ips := PeerIPsFromHosts(peers)
	if len(ips) != 2 {
		t.Fatalf("want 2 ips, got %v", ips)
	}
	// 无空 IP 时，台数与 ips 长度一致
	if SameSvrOwnerCount(a, pool) != len(ips) {
		t.Fatalf("count mismatch: peers=%d ips=%d", SameSvrOwnerCount(a, pool), len(ips))
	}
}

func TestSameSvrOwnerIPs_EmptyAsset(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "", 100, model.RESOURCE_TYPE_PUBLIC, nil)
	peers := ListSameSvrOwnerPeers(a, []model.TbRpDetail{a})
	ips := PeerIPsFromHosts(peers)
	if len(peers) != 0 || len(ips) != 0 {
		t.Fatalf("empty asset should yield empty ips, got peers=%d ips=%v", len(peers), ips)
	}
}

func TestPeerIPsFromHosts_SkipEmptyAndDedup(t *testing.T) {
	peers := []model.TbRpDetail{
		{IP: "127.0.0.2"},
		{IP: ""},
		{IP: "  "},
		{IP: "127.0.0.1"},
		{IP: "127.0.0.2"},
	}
	ips := PeerIPsFromHosts(peers)
	if len(ips) != 2 {
		t.Fatalf("want 2 unique non-empty ips, got %v", ips)
	}
	// IP 接口 count 语义：与 len(ips) 一致，可小于 peer 台数
	if len(ips) >= len(peers) {
		t.Fatalf("dedup/skip should shrink ips relative to peers")
	}
}

func TestSameSvrOwnerIPs_WhitespaceAssetTreatedEmpty(t *testing.T) {
	a := host(t, 1, "127.0.0.1", "   ", 100, model.RESOURCE_TYPE_PUBLIC, nil)
	peers := ListSameSvrOwnerPeers(a, []model.TbRpDetail{a})
	if len(peers) != 0 {
		t.Fatalf("whitespace asset should be empty via IsEmpty, got %d", len(peers))
	}
}
