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
	"fmt"
	"time"

	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/go-pubpkg/logger"
)

// DissolveHostCheck 巡检资源池空闲主机是否待裁撤，命中则标记为 Dissolved
func DissolveHostCheck() (err error) {
	var machines []model.TbRpDetail
	if err = model.DB.Self.Table(model.TbRpDetailName()).
		Where("status = ? ", model.Unused).
		Find(&machines).Error; err != nil {
		logger.Error("get unused machines failed %s", err.Error())
		return err
	}
	if len(machines) == 0 {
		logger.Info("no unused machines found for dissolve check")
		return nil
	}

	var failedBatches int
	var lastErr error
	for _, mgp := range lo.Chunk(machines, 50) {
		bkHostIds := make([]int, 0, len(mgp))
		for _, m := range mgp {
			bkHostIds = append(bkHostIds, m.BkHostID)
		}
		dissolvedHostIds, checkErr := dbmapi.CheckHostIsDissolved(bkHostIds)
		if checkErr != nil {
			logger.Error("check dissolve hosts failed %s", checkErr.Error())
			failedBatches++
			lastErr = checkErr
			continue
		}
		if len(dissolvedHostIds) == 0 {
			logger.Info("no dissolved hosts found in this batch")
			continue
		}
		logger.Info("found dissolved hosts %v", dissolvedHostIds)
		err = model.DB.Self.Table(model.TbRpDetailName()).
			Where("bk_host_id in (?) and status = ?", dissolvedHostIds, model.Unused).
			Updates(map[string]interface{}{"status": model.Dissolved, "update_time": time.Now()}).
			Error
		if err != nil {
			logger.Error("update machine status to Dissolved failed %s", err.Error())
			return err
		}
	}
	if failedBatches > 0 {
		return fmt.Errorf("dissolve check failed for %d batches, last: %w", failedBatches, lastErr)
	}
	return nil
}
