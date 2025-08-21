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
	"k8s-dbs/metadata/model"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func InitComponentTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_component;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_component table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_component table")
		return nil, err
	}
	return db, nil
}

func TestCreateComponent(t *testing.T) {
	db, err := InitComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)

	component := &model.K8sCrdComponentModel{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}

	addedComponent, err := dbAccess.Create(component)
	assert.NoError(t, err)

	assert.Equal(t, component.ComponentName, addedComponent.ComponentName)
	assert.Equal(t, component.CrdClusterID, addedComponent.CrdClusterID)
	assert.Equal(t, component.Status, addedComponent.Status)
}

func TestDeleteComponent(t *testing.T) {
	db, err := InitComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	component := &model.K8sCrdComponentModel{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}
	_, err = dbAccess.Create(component)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateComponent(t *testing.T) {
	db, err := InitComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	component := &model.K8sCrdComponentModel{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}
	_, err = dbAccess.Create(component)
	assert.NoError(t, err)

	newComponent := &model.K8sCrdComponentModel{
		ID:            1,
		ComponentName: "component-03",
		CrdClusterID:  2,
		Status:        "Disable",
		Description:   "update success",
	}
	rows, err := dbAccess.Update(newComponent)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetComponent(t *testing.T) {
	db, err := InitComponentTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	component := &model.K8sCrdComponentModel{
		ComponentName: "component-01",
		CrdClusterID:  1,
		Status:        "Enable",
		Description:   "desc",
	}
	_, err = dbAccess.Create(component)
	assert.NoError(t, err)

	foundComponent, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, component.ComponentName, foundComponent.ComponentName)
	assert.Equal(t, component.CrdClusterID, foundComponent.CrdClusterID)
	assert.Equal(t, component.Status, foundComponent.Status)
}
