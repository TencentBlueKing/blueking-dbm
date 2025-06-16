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

func SetUpTestDBForOpDef() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_operation_definition;").Error; err != nil {
		fmt.Println("Failed to drop tb_operation_definition table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.OperationDefinitionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_operation_definition table")
		return nil, err
	}
	return db, nil
}

func TestListOpDef(t *testing.T) {
	db, err := SetUpTestDBForOpDef()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewOperationDefinitionDbAccess(db)

	testOpDefs := []model.OperationDefinitionModel{
		{
			OperationName:   "CreateCluster",
			OperationTarget: "Cluster",
			Active:          true,
			Description:     "desc",
		},
		{
			OperationName:   "DeleteCluster",
			OperationTarget: "Cluster",
			Active:          true,
			Description:     "desc",
		},
		{
			OperationName:   "RestartComponent",
			OperationTarget: "Component",
			Active:          true,
			Description:     "desc",
		},
		{
			OperationName:   "StopComponent",
			OperationTarget: "Component",
			Active:          true,
			Description:     "desc",
		},
	}

	for _, opDef := range testOpDefs {
		createdDef, err := dbAccess.Create(&opDef)
		assert.NoError(t, err, "Failed to create operation definition: %v", createdDef.OperationName)
		assert.Equal(t, opDef.OperationName, createdDef.OperationName)
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	opDefs, rows, err := dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(4), rows)
	assert.Equal(t, len(testOpDefs), len(opDefs))

	opDefNames := make(map[string]bool)
	for _, opDef := range opDefs {
		opDefNames[opDef.OperationName] = true
	}

	for _, expected := range testOpDefs {
		assert.True(t, opDefNames[expected.OperationName], "Expected operation defition %s not found in the result", expected.OperationName)
	}
}
