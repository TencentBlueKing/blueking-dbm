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
	"fmt"

	rf "github.com/gin-gonic/gin"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
)

// SameSvrOwnerIPsParam 查询同母机计入集合 IP 列表
type SameSvrOwnerIPsParam struct {
	BkHostID int `json:"bk_host_id" binding:"required"`
}

// ListSameSvrOwnerIPs 返回计入规则下的同母机 IP 列表（旁侧复制用）
func (c *MachineResourceHandler) ListSameSvrOwnerIPs(r *rf.Context) {
	var input SameSvrOwnerIPsParam
	if c.Prepare(r, &input) != nil {
		return
	}
	if input.BkHostID <= 0 {
		c.SendResponse(r, errno.ErrErrInvalidParam.AddErr(fmt.Errorf("bk_host_id is required")), nil)
		return
	}

	var current model.TbRpDetail
	err := model.DB.Self.Table(model.TbRpDetailName()).
		Where("bk_host_id = ? AND status = ?", input.BkHostID, model.Unused).
		Take(&current).Error
	if err != nil {
		c.SendResponse(r, errno.ErrDBQuery.AddErr(fmt.Errorf("host %d not found in unused pool", input.BkHostID)), nil)
		return
	}

	resp := map[string]interface{}{
		"bk_host_id":            current.BkHostID,
		"bk_svr_owner_asset_id": current.BkSvrOwnerAssetID,
		"count":                 0,
		"ips":                   []string{},
	}
	if cmutil.IsEmpty(current.BkSvrOwnerAssetID) {
		c.SendResponse(r, nil, resp)
		return
	}

	pool, err := loadUnusedSameSvrOwnerPool([]string{current.BkSvrOwnerAssetID})
	if err != nil {
		c.SendResponse(r, errno.ErrDBQuery.AddErr(err), nil)
		return
	}
	peers := ListSameSvrOwnerPeers(current, pool)
	ips := PeerIPsFromHosts(peers)
	// count 与可复制 IP 列表长度一致（去空/去重后）
	resp["count"] = len(ips)
	resp["ips"] = ips
	c.SendResponse(r, nil, resp)
}
