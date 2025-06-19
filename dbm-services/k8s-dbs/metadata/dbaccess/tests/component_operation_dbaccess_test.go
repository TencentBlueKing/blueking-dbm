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
	"k8s-dbs/common/entity"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/dbaccess/model"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func SetUpTestDBForComponentOp() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_component_operation;").Error; err != nil {
		fmt.Println("Failed to drop tb_component_operation table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.ComponentOperationModel{}); err != nil {
		fmt.Println("Failed to migrate tb_component_operation table")
		return nil, err
	}
	return db, nil
}

func TestListComponentOp(t *testing.T) {
	db, err := SetUpTestDBForComponentOp()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewComponentOperationDbAccess(db)

	testComponentOps := []model.ComponentOperationModel{
		{
			AddonType:        "surrealdb",
			AddonVersion:     "1.0.0",
			ComponentName:    "surreal",
			ComponentVersion: "2.2.1",
			OperationID:      1,
			Active:           true,
			Description:      "desc",
		},
		{
			AddonType:        "vm",
			AddonVersion:     "1.0.0",
			ComponentName:    "vmselect",
			ComponentVersion: "1.115",
			OperationID:      1,
			Active:           true,
			Description:      "desc",
		},
	}

	for _, componentOp := range testComponentOps {
		createdOp, err := dbAccess.Create(&componentOp)
		assert.NoError(t, err)
		assert.Equal(t, componentOp.ComponentName, createdOp.ComponentName)
		assert.Equal(t, componentOp.ComponentVersion, createdOp.ComponentVersion)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}

	ComponentOps, rows, err := dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(2), rows)
	assert.Equal(t, len(testComponentOps), len(ComponentOps))
}
