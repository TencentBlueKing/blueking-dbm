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
	"sort"
	"strings"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
)

// ListSameSvrOwnerPeers 按当前机视角返回计入规则下的同母机同伴（含本机）。
// pool 应为 Unused 候选；空固资号返回 nil。
func ListSameSvrOwnerPeers(current model.TbRpDetail, pool []model.TbRpDetail) []model.TbRpDetail {
	if cmutil.IsEmpty(current.BkSvrOwnerAssetID) {
		return nil
	}
	curLabels := unmarshalHostLabels(current.Labels)
	var peers []model.TbRpDetail
	for _, p := range pool {
		if p.BkSvrOwnerAssetID != current.BkSvrOwnerAssetID {
			continue
		}
		if !matchSameSvrOwnerBizAndLabels(current, curLabels, p) {
			continue
		}
		if !matchSameSvrOwnerRsType(current, p) {
			continue
		}
		peers = append(peers, p)
	}
	return peers
}

// SameSvrOwnerCount 同母机台数（含本机）；空固资号为 0。
func SameSvrOwnerCount(current model.TbRpDetail, pool []model.TbRpDetail) int {
	return len(ListSameSvrOwnerPeers(current, pool))
}

// GroupBySvrOwnerAsset 按母机固资号分组（跳过空固资）。
func GroupBySvrOwnerAsset(pool []model.TbRpDetail) map[string][]model.TbRpDetail {
	m := make(map[string][]model.TbRpDetail)
	for _, h := range pool {
		if cmutil.IsEmpty(h.BkSvrOwnerAssetID) {
			continue
		}
		m[h.BkSvrOwnerAssetID] = append(m[h.BkSvrOwnerAssetID], h)
	}
	return m
}

// ListSameSvrOwnerPeersGrouped 使用预分组结果计算 peers，避免每次扫全池。
func ListSameSvrOwnerPeersGrouped(current model.TbRpDetail, byAsset map[string][]model.TbRpDetail) []model.TbRpDetail {
	if cmutil.IsEmpty(current.BkSvrOwnerAssetID) {
		return nil
	}
	return ListSameSvrOwnerPeers(current, byAsset[current.BkSvrOwnerAssetID])
}

// CollectSvrOwnerAssetIDs 收集非空母机固资号（去重）。
func CollectSvrOwnerAssetIDs(hosts []model.TbRpDetail) []string {
	seen := make(map[string]struct{}, len(hosts))
	var ids []string
	for _, h := range hosts {
		if cmutil.IsEmpty(h.BkSvrOwnerAssetID) {
			continue
		}
		if _, ok := seen[h.BkSvrOwnerAssetID]; ok {
			continue
		}
		seen[h.BkSvrOwnerAssetID] = struct{}{}
		ids = append(ids, h.BkSvrOwnerAssetID)
	}
	return ids
}

// FillSameSvrOwnerCounts 用分组池为详情填 SameSvrOwnerCount。
func FillSameSvrOwnerCounts(details []model.TbRpDetail, byAsset map[string][]model.TbRpDetail) {
	for i := range details {
		details[i].SameSvrOwnerCount = len(ListSameSvrOwnerPeersGrouped(details[i], byAsset))
	}
}

// PeerIPsFromHosts 提取 IP 并稳定排序去重。
func PeerIPsFromHosts(peers []model.TbRpDetail) []string {
	seen := make(map[string]struct{}, len(peers))
	ips := make([]string, 0, len(peers))
	for _, p := range peers {
		ip := strings.TrimSpace(p.IP)
		if ip == "" {
			continue
		}
		if _, ok := seen[ip]; ok {
			continue
		}
		seen[ip] = struct{}{}
		ips = append(ips, ip)
	}
	sort.Strings(ips)
	return ips
}

func unmarshalHostLabels(raw json.RawMessage) []string {
	if len(raw) == 0 || string(raw) == "null" {
		return nil
	}
	var labels []string
	if err := json.Unmarshal(raw, &labels); err != nil {
		return nil
	}
	return labels
}

func labelsIntersect(a, b []string) bool {
	if len(a) == 0 || len(b) == 0 {
		return false
	}
	set := make(map[string]struct{}, len(a))
	for _, x := range a {
		set[x] = struct{}{}
	}
	for _, y := range b {
		if _, ok := set[y]; ok {
			return true
		}
	}
	return false
}

// matchSameSvrOwnerBizAndLabels 表 A：业务与标签。
func matchSameSvrOwnerBizAndLabels(cur model.TbRpDetail, curLabels []string, p model.TbRpDetail) bool {
	pLabels := unmarshalHostLabels(p.Labels)
	curEmpty := len(curLabels) == 0
	pEmpty := len(pLabels) == 0
	if curEmpty {
		if !pEmpty {
			return false
		}
		if cur.DedicatedBiz == 0 {
			return true
		}
		return p.DedicatedBiz == 0 || p.DedicatedBiz == cur.DedicatedBiz
	}
	if p.DedicatedBiz == 0 || p.DedicatedBiz != cur.DedicatedBiz {
		return false
	}
	return labelsIntersect(curLabels, pLabels)
}

// matchSameSvrOwnerRsType 表 B：所属 DB。
func matchSameSvrOwnerRsType(cur, p model.TbRpDetail) bool {
	curType := model.NormalizeResourceType(cur.RsType)
	if curType == "" || curType == model.RESOURCE_TYPE_PUBLIC {
		return true
	}
	pType := model.NormalizeResourceType(p.RsType)
	return pType == model.RESOURCE_TYPE_PUBLIC || pType == curType
}
