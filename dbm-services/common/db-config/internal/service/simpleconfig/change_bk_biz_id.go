// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"

	"gorm.io/gorm"
)

// ChangeBkBizId 修改集群的业务 id
// 返回影响 tb_config_versioned 表的记录数
func ChangeBkBizId(r *api.ChangeBkBizIdReq, opUser string) (*api.ChangeBkBizIdResp, error) {
	var rowsAffected int64
	txErr := model.DB.Self.Transaction(func(tx *gorm.DB) error {
		updateVersioned := tx.Model(&model.ConfigVersionedModel{}).
			Where("bk_biz_id = ? and level_value in ? and level_name = ?",
				r.BKBizID, r.ClusterDomains, constvar.LevelCluster).
			Update("bk_biz_id", r.NewBKBizID)
		if err := updateVersioned.Error; err != nil {
			return err
		} else {
			rowsAffected = updateVersioned.RowsAffected
		}

		updateConfigNode := tx.Model(&model.ConfigModel{}).
			Where("bk_biz_id = ? and level_value in ? and level_name = ?",
				r.BKBizID, r.ClusterDomains, constvar.LevelCluster).
			Update("bk_biz_id", r.NewBKBizID)
		if err := updateConfigNode.Error; err != nil {
			return err
		}

		updateFileNode := tx.Model(&model.ConfigFileNodeModel{}).
			Where("bk_biz_id = ? and level_value in ? and level_name = ?",
				r.BKBizID, r.ClusterDomains, constvar.LevelCluster).
			Update("bk_biz_id", r.NewBKBizID)
		if err := updateFileNode.Error; err != nil {
			return err
		}
		return nil
	})

	if txErr == nil {
		return &api.ChangeBkBizIdResp{ClustersAffected: rowsAffected}, nil
	}
	return nil, txErr
}
