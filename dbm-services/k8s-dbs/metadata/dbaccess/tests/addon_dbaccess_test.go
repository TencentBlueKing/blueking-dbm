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
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func SetUpTestDBForStorageAddon() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MysqlURL), &gorm.Config{})
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
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	storageAddon := &model.K8sCrdStorageAddonModel{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedStorageAddon, err := dbAccess.Create(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedStorageAddon)

	var foundStorageAddon model.K8sCrdStorageAddonModel
	err = db.First(&foundStorageAddon, "addon_name=?", "myaddon").Error
	assert.NoError(t, err, "Failed to query storageAddon")
	assert.Equal(t, storageAddon.AddonName, foundStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundStorageAddon.AddonType)
	assert.Equal(t, storageAddon.Metadata, foundStorageAddon.Metadata)
	assert.Equal(t, storageAddon.Spec, foundStorageAddon.Spec)
	assert.Equal(t, storageAddon.Active, foundStorageAddon.Active)
}

func TestDeleteStorageAddon(t *testing.T) {
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	storageAddon := &model.K8sCrdStorageAddonModel{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedstorageAddon, err := dbAccess.Create(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedstorageAddon)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err, "Failed to delete storageAddon")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateStorageAddon(t *testing.T) {
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	storageAddon := &model.K8sCrdStorageAddonModel{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedstorageAddon, err := dbAccess.Create(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created cluster %+v\n", addedstorageAddon)

	updateStorageAddon := &model.K8sCrdStorageAddonModel{
		ID:            1,
		AddonName:     "myaddon2",
		AddonCategory: "Graph",
		AddonType:     "surrealdb2",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":1}",
		Active:        false,
		Description:   "desc",
		UpdatedAt:     time.Now(),
	}
	rows, err := dbAccess.Update(updateStorageAddon)
	assert.NoError(t, err, "Failed to update storageAddon")
	assert.Equal(t, uint64(1), rows)
}

func TestGetStorageAddon(t *testing.T) {
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	storageAddon := &model.K8sCrdStorageAddonModel{
		AddonName:     "myaddon",
		AddonCategory: "Graph",
		AddonType:     "surrealdb",
		Metadata:      "{\"namespace\":\"default\"}",
		Spec:          "{\"replicas\":3}",
		Active:        true,
		Description:   "desc",
	}

	addedstorageAddon, err := dbAccess.Create(storageAddon)
	assert.NoError(t, err, "Failed to create storageAddon")
	fmt.Printf("Created storageAddon %+v\n", addedstorageAddon)

	foundStorageAddon, err := dbAccess.FindByID(1)
	assert.NoError(t, err, "Failed to find storageAddon")
	assert.Equal(t, storageAddon.AddonName, foundStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundStorageAddon.AddonType)
	assert.Equal(t, storageAddon.Metadata, foundStorageAddon.Metadata)
	assert.Equal(t, storageAddon.Spec, foundStorageAddon.Spec)
	assert.Equal(t, storageAddon.Active, foundStorageAddon.Active)
}
