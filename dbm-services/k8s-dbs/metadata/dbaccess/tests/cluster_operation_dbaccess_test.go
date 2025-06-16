/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package tests

import (
	"fmt"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/utils"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func SetUpTestDBForClusterOp() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_cluster_operation;").Error; err != nil {
		fmt.Println("Failed to drop tb_cluster_operation table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.ClusterOperationModel{}); err != nil {
		fmt.Println("Failed to migrate tb_cluster_operation table")
		return nil, err
	}
	return db, nil
}

func TestListClusterOp(t *testing.T) {
	db, err := SetUpTestDBForClusterOp()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewClusterOperationDbAccess(db)

	testClusterOps := []model.ClusterOperationModel{
		{
			AddonType:    "SurrealDB",
			AddonVersion: "1.0.0",
			OperationID:  1,
			Active:       true,
			Description:  "desc",
		},
		{
			AddonType:    "VM",
			AddonVersion: "1.0.0",
			OperationID:  1,
			Active:       true,
			Description:  "desc",
		},
	}

	for _, clusterOp := range testClusterOps {
		createdOp, err := dbAccess.Create(&clusterOp)
		assert.NoError(t, err)
		assert.Equal(t, clusterOp.AddonType, createdOp.AddonType)
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	clusterOps, rows, err := dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(2), rows)
	assert.Equal(t, len(testClusterOps), len(clusterOps), "Expected number to match")
}
