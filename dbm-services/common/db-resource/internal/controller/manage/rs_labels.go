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
	rf "github.com/gin-gonic/gin"

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
		logger.Error("Preare Error %s", err.Error())
		return
	}
	db := model.DB.Self.Table("tb_rp_detail").Exec("update tb_rp_detail set labels=? where bk_host_id in (?)",
		model.JsonMerge("labels", input.Labels), input.BkHostIds)
	err := db.Error
	if err != nil {
		logger.Error("failed to add labels:%s", err.Error())
		c.SendResponse(r, err, nil)
		return
	}
	c.SendResponse(r, nil, map[string]interface{}{"affected_count": db.RowsAffected})
}
