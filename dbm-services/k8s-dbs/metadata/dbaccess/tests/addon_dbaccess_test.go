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
	"time"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func SetUpTestDBForStorageAddon() (*gorm.DB, error) {
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
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	storageAddon := &model.K8sCrdStorageAddonModel{
		AddonName:          "myaddon",
		AddonCategory:      "Graph",
		AddonType:          "surrealdb",
		AddonVersion:       "1.0.0",
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             true,
		Description:        "desc",
	}

	addedStorageAddon, err := dbAccess.Create(storageAddon)
	assert.NoError(t, err)
	assert.Equal(t, storageAddon.AddonName, addedStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, addedStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, addedStorageAddon.AddonType)
	assert.Equal(t, storageAddon.AddonVersion, addedStorageAddon.AddonVersion)
	assert.Equal(t, storageAddon.RecommendedVersion, addedStorageAddon.RecommendedVersion)
	assert.Equal(t, storageAddon.Topologies, addedStorageAddon.Topologies)
	assert.Equal(t, storageAddon.Releases, addedStorageAddon.Releases)
	assert.Equal(t, storageAddon.Active, addedStorageAddon.Active)
}

func TestDeleteStorageAddon(t *testing.T) {
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	storageAddon := &model.K8sCrdStorageAddonModel{
		AddonName:          "myaddon",
		AddonCategory:      "Graph",
		AddonType:          "surrealdb",
		AddonVersion:       "1.0.0",
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             true,
		Description:        "desc",
	}

	_, err = dbAccess.Create(storageAddon)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateStorageAddon(t *testing.T) {
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	storageAddon := &model.K8sCrdStorageAddonModel{
		AddonName:          "myaddon",
		AddonCategory:      "Graph",
		AddonType:          "surrealdb",
		AddonVersion:       "1.0.0",
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             true,
		Description:        "desc",
	}

	_, err = dbAccess.Create(storageAddon)
	assert.NoError(t, err)

	updateStorageAddon := &model.K8sCrdStorageAddonModel{
		ID:                 1,
		AddonName:          "myaddon2",
		AddonCategory:      "Graph",
		AddonType:          "surrealdb2",
		AddonVersion:       "1.0.0",
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             false,
		Description:        "desc",
		UpdatedAt:          time.Now(),
	}
	rows, err := dbAccess.Update(updateStorageAddon)
	assert.NoError(t, err)
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
		AddonVersion:  "1.0.0",
		Active:        true,
		Description:   "desc",
	}

	_, err = dbAccess.Create(storageAddon)
	assert.NoError(t, err)

	foundStorageAddon, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, storageAddon.AddonName, foundStorageAddon.AddonName)
	assert.Equal(t, storageAddon.AddonCategory, foundStorageAddon.AddonCategory)
	assert.Equal(t, storageAddon.AddonType, foundStorageAddon.AddonType)
	assert.Equal(t, storageAddon.AddonVersion, foundStorageAddon.AddonVersion)
	assert.Equal(t, storageAddon.Active, foundStorageAddon.Active)
}

func TestListStorageAddon(t *testing.T) {
	db, err := SetUpTestDBForStorageAddon()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	testAddons := []model.K8sCrdStorageAddonModel{
		{
			AddonName:          "surreal",
			AddonCategory:      "Graph",
			AddonType:          "SurrealDB",
			AddonVersion:       "1.0.0",
			RecommendedVersion: "1.0.0",
			Topologies:         "{}",
			Releases:           "{}",
			Active:             true,
			Description:        "desc",
		},
		{
			AddonName:          "vm",
			AddonCategory:      "Time-Series",
			AddonType:          "VictoriaMetric",
			AddonVersion:       "1.0.0",
			RecommendedVersion: "1.0.0",
			Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
			Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
			Active:             true,
			Description:        "desc",
		},
	}

	for _, addon := range testAddons {
		createdAddon, err := dbAccess.Create(&addon)
		assert.NoError(t, err, "Failed to create storage addon: %v", addon.AddonName)
		assert.NotNil(t, createdAddon, "Created addon should not be nil")
		assert.Equal(t, addon.AddonName, createdAddon.AddonName, "Addon name mismatch")
	}

	pagination := utils.Pagination{
		Page:  0,
		Limit: 10,
	}

	addons, rows, err := dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(2), rows)
	assert.Equal(t, len(testAddons), len(addons))

	addonNames := make(map[string]bool)
	for _, addon := range addons {
		addonNames[addon.AddonName] = true
	}

	for _, expectedAddon := range testAddons {
		assert.True(t, addonNames[expectedAddon.AddonName], "Expected addon %s not found in the result", expectedAddon.AddonName)
	}
}
