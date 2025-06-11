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
	"k8s-dbs/metadata/utils"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func initAddonTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_storageaddon;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_storageaddon table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdStorageAddonModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_storageaddon table")
		return nil, err
	}
	return db, nil
}

func TestCreateStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		AddonVersion:  "1.0.0",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	var foundStorageAddon model.K8sCrdStorageAddonModel
	err = db.First(&foundStorageAddon, "addon_name=?", "myaddon").Error
	assert.NoError(t, err, "Failed to query storageAddon")
	assert.Equal(t, storageAddon.AddonName, foundStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundStorageAddon.AddonType)
	assert.Equal(t, storageAddon.AddonVersion, foundStorageAddon.AddonVersion)
	assert.Equal(t, storageAddon.Active, foundStorageAddon.Active)
}

func TestDeleteStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		AddonVersion:  "1.0.0",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	rows, err := addonProvider.DeleteStorageAddonByID(1)
	assert.NoError(t, err, "Failed to delete storageAddon")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		AddonVersion:  "1.0.0",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	updateStorageAddon := &entitys.K8sCrdStorageAddonEntity{
		ID:            1,
		AddonName:     "myaddon2",
		AddonCategory: "Graph",
		AddonType:     "surrealdb2",
		AddonVersion:  "1.0.0",
		Active:        false,
		Description:   "desc",
		UpdatedAt:     time.Now(),
	}
	rows, err := addonProvider.UpdateStorageAddon(updateStorageAddon)
	assert.NoError(t, err, "Failed to update storageAddon")
	assert.Equal(t, uint64(1), rows)
}

func TestGetStorageAddon(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	storageAddon := &entitys.K8sCrdStorageAddonEntity{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		AddonVersion:  "1.0.0",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := addonProvider.CreateStorageAddon(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	foundStorageAddon, err := addonProvider.FindStorageAddonByID(1)
	assert.NoError(t, err, "Failed to find storageAddon")
	assert.Equal(t, storageAddon.AddonName, foundStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundStorageAddon.AddonType)
	assert.Equal(t, storageAddon.AddonVersion, foundStorageAddon.AddonVersion)
	assert.Equal(t, storageAddon.Active, foundStorageAddon.Active)
}

func TestListStorageAddons(t *testing.T) {
	db, err := initAddonTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)

	// 创建测试数据
	testAddons := []entitys.K8sCrdStorageAddonEntity{
		{
			AddonName:     "surreal",
			AddonCategory: "Graph",
			AddonType:     "SurrealDB",
			AddonVersion:  "1.0.0",
			Active:        true,
			Description:   "desc",
		},
		{
			AddonName:     "vm",
			AddonCategory: "Time-Series",
			AddonType:     "VictoriaMetric",
			AddonVersion:  "1.0.0",
			Active:        true,
			Description:   "desc",
		},
	}

	for _, addon := range testAddons {
		createdAddon, err := addonProvider.CreateStorageAddon(&addon)
		assert.NoError(t, err, "Failed to create storage addon: %v", addon.AddonName)
		assert.NotNil(t, createdAddon, "Created addon should not be nil")
		assert.Equal(t, addon.AddonName, createdAddon.AddonName, "Addon name mismatch")
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	addons, err := addonProvider.ListStorageAddons(pagination)
	assert.NoError(t, err, "Failed to list storage addons")
	assert.Equal(t, len(testAddons), len(addons))

	addonNames := make(map[string]bool)
	for _, addon := range addons {
		addonNames[addon.AddonName] = true
	}

	for _, expectedAddon := range testAddons {
		assert.True(t, addonNames[expectedAddon.AddonName], "Expected addon %s not found in the result", expectedAddon.AddonName)
	}
}
