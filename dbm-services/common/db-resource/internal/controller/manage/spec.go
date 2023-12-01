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
	"strconv"

	"github.com/gin-gonic/gin"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"
)

// SpecCheckInput TODO
type SpecCheckInput struct {
	ResourceType string     `json:"resource_type"`
	BkCloudId    int        `json:"bk_cloud_id"`
	ForbizId     int        `json:"for_biz_id"`
	Details      []SpecInfo `json:"details" binding:"required,gt=0,dive"`
}

// SpecInfo TODO
type SpecInfo struct {
	GroupMark    string           `json:"group_mark" binding:"required" `
	DeviceClass  []string         `json:"device_class"`
	Spec         apply.Spec       `json:"spec"`
	StorageSpecs []apply.DiskSpec `json:"storage_spec"`
}

// SpecSum TODO
func (m MachineResourceHandler) SpecSum(r *gin.Context) {
	var input SpecCheckInput
	requestId := r.GetString("request_id")
	if err := m.Prepare(r, &input); err != nil {
		m.SendResponse(r, err, err.Error(), requestId)
		return
	}
	rpdata := make(map[string]int64)
	for _, item := range input.Details {
		var count int64
		s := &apply.SearchContext{
			IntetionBkBizId: input.ForbizId,
			RsType:          input.ResourceType,
			ApplyObjectDetail: &apply.ApplyObjectDetail{
				GroupMark:    item.GroupMark,
				DeviceClass:  item.DeviceClass,
				Spec:         item.Spec,
				StorageSpecs: item.StorageSpecs,
			},
		}
		for _, fn := range s.Matcher() {
			db := model.DB.Self.Table(model.TbRpDetailName()).Select("count(*)")
			db.Where("gse_agent_status_code = ? ", bk.GSE_AGENT_OK)
			db.Where(" bk_cloud_id = ? and status = ?  ", input.BkCloudId, model.Unused)
			// 如果没有指定资源类型，表示只能选择无资源类型标签的资源
			// 没有资源类型标签的资源可以被所有其他类型使用
			if input.ForbizId > 0 {
				db.Where("( ? or JSON_LENGTH(dedicated_bizs)<=0 )", model.JSONQuery("").Contains([]string{
					strconv.Itoa(input.ForbizId)}))
			}
			if cmutil.IsEmpty(input.ResourceType) {
				db.Where("JSON_LENGTH(rs_types) <= 0")
			} else {
				db.Where("( ? or JSON_LENGTH(rs_types) <= 0 )", model.JSONQuery("rs_types").Contains([]string{input.ResourceType}))
			}
			s.MatchStorage(db)
			fn(db)
			var cnt int64
			if err := db.Scan(&cnt).Error; err != nil {
				logger.Error("query pre check count failed %s", err.Error())
				m.SendResponse(r, errno.ErrDBQuery.AddErr(err), err.Error(), requestId)
				return
			}
			count += cnt
		}
		rpdata[item.GroupMark] = count
	}
	m.SendResponse(r, nil, rpdata, requestId)
}
