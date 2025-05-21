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
	"k8s-dbs/metadata/provider"
	entitys "k8s-dbs/metadata/provider/entity"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func initCmpdTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_componentdefinition;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_componentdefinition table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentDefinitionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_componentdefinition table")
		return nil, err
	}
	return db, nil
}

func TestCreateComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpdDbAccess(db)

	cmpdProvider := provider.NewK8sCrdCmpdProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateCmpd(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	var foundCmpd model.K8sCrdComponentDefinitionModel
	err = db.First(&foundCmpd, "componentdefinition_name=?", "mycmpd").Error
	assert.NoError(t, err, "Failed to query componentDefinition")
	assert.Equal(t, cmpd.ComponentDefinitionName, foundCmpd.ComponentDefinitionName)
	assert.Equal(t, cmpd.AddonID, foundCmpd.AddonID)
	assert.Equal(t, cmpd.DefaultVersion, foundCmpd.DefaultVersion)
	assert.Equal(t, cmpd.Metadata, foundCmpd.Metadata)
	assert.Equal(t, cmpd.Spec, foundCmpd.Spec)
	assert.Equal(t, cmpd.Active, foundCmpd.Active)
}

func TestDeletComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpdDbAccess(db)

	cmpdProvider := provider.NewK8sCrdCmpdProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateCmpd(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	rows, err := cmpdProvider.DeleteCmpdByID(1)
	assert.NoError(t, err, "Failed to delete componentDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpdDbAccess(db)

	cmpdProvider := provider.NewK8sCrdCmpdProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateCmpd(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	updatedCmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ID:                      1,
		ComponentDefinitionName: "mycmpd2",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default2\"}",
		Spec:                    "{\"replicas\":2}",
		Active:                  false,
		Description:             "desc",
		UpdatedAt:               time.Now(),
	}
	rows, err := cmpdProvider.UpdateCmpd(updatedCmpd)
	assert.NoError(t, err, "Failed to update componentDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestGetComponentDefinition(t *testing.T) {
	db, err := initCmpdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpdDbAccess(db)

	cmpdProvider := provider.NewK8sCrdCmpdProvider(dbAccess)

	cmpd := &entitys.K8sCrdComponentDefinitionEntity{
		ComponentDefinitionName: "mycmpd",
		AddonID:                 uint64(1),
		DefaultVersion:          "2.1.3",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":3}",
		Active:                  true,
		Description:             "desc",
	}

	addedCmpd, err := cmpdProvider.CreateCmpd(cmpd)
	assert.NoError(t, err, "Failed to create componentDefinition")
	fmt.Printf("Created componentDefinition %+v\n", addedCmpd)

	foundCmpd, err := cmpdProvider.FindCmpdByID(1)
	assert.NoError(t, err, "Failed to find componentDefinition")
	assert.Equal(t, cmpd.ComponentDefinitionName, foundCmpd.ComponentDefinitionName)
	assert.Equal(t, cmpd.AddonID, foundCmpd.AddonID)
	assert.Equal(t, cmpd.DefaultVersion, foundCmpd.DefaultVersion)
	assert.Equal(t, cmpd.Metadata, foundCmpd.Metadata)
	assert.Equal(t, cmpd.Spec, foundCmpd.Spec)
	assert.Equal(t, cmpd.Active, foundCmpd.Active)
}
