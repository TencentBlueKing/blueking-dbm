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

	rf "github.com/gin-gonic/gin"
	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/logger"
)

// AddLabelsParam add labels param
type AddLabelsParam struct {
	BkHostIds []int    `json:"bk_host_ids"  binding:"required,gt=0,dive"`
	Labels    []string `json:"labels,omitempty"`
}

// AddLabels add labels
func (c *MachineResourceHandler) AddLabels(r *rf.Context) {
	var input AddLabelsParam
	if err := c.Prepare(r, &input); err != nil {
		logger.Error("Prepare Error %s", err.Error())
		return
	}
	var resources []model.TbRpDetail
	if err := model.DB.Self.Table("tb_rp_detail").Where("bk_host_id in (?)", input.BkHostIds).
		Find(&resources).Error; err != nil {
		logger.Error("failed to query resources: %s", err.Error())
		c.SendResponse(r, err, nil)
		return
	}
	var affected_count int64
	for _, resource := range resources {
		var labels []string
		err := json.Unmarshal([]byte(resource.Labels), &labels)
		if err != nil {
			logger.Error("failed to unmarshal labels for host %d: %s", resource.BkHostID, err.Error())
			c.SendResponse(r, err, nil)
			return
		}
		if len(labels) == 0 {
			labels = input.Labels
		} else {
			labels = lo.Uniq(append(labels, input.Labels...))
		}
		labelsJSON, err := json.Marshal(labels)
		if err != nil {
			logger.Error("failed to marshal labels: %s", err.Error())
			c.SendResponse(r, err, nil)
			return
		}
		err = model.DB.Self.Table("tb_rp_detail").Where("bk_host_id = ?", resource.BkHostID).
			Updates(map[string]interface{}{"labels": string(labelsJSON)}).Error
		if err != nil {
			logger.Error("failed to update labels for host %d: %s", resource.BkHostID, err.Error())
			c.SendResponse(r, err, nil)
			return
		}
		affected_count++
	}
	c.SendResponse(r, nil, map[string]interface{}{"affected_count": affected_count})
}
