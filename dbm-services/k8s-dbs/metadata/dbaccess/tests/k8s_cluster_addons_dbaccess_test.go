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
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/model"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func SetUpTestDBForClusterAddons() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_cluster_addons;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_cluster_addons table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sClusterAddonsModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_cluster_addons table")
		return nil, err
	}
	return db, nil
}

func TestCreatClusterAddons(t *testing.T) {
	db, err := SetUpTestDBForClusterAddons()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterAddonsDbAccess(db)

	addon := &model.K8sClusterAddonsModel{
		AddonID:        1,
		K8sClusterName: "bcs-k8s-xxx",
	}

	addedStorageAddon, err := dbAccess.Create(addon)
	assert.NoError(t, err)
	assert.Equal(t, uint64(0x1), addedStorageAddon.ID)
	assert.Equal(t, uint64(0x1), addedStorageAddon.AddonID)
	assert.Equal(t, "bcs-k8s-xxx", addedStorageAddon.K8sClusterName)
}

func TestFindClusterAddonsByParams(t *testing.T) {
	db, err := SetUpTestDBForClusterAddons()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterAddonsDbAccess(db)

	addon := &model.K8sClusterAddonsModel{
		AddonID:        1,
		K8sClusterName: "bcs-k8s-xxx",
	}

	_, err = dbAccess.Create(addon)
	assert.NoError(t, err)

	clusterAddonParams := &metaentity.K8sClusterAddonQueryParams{
		K8sClusterName: "bcs-k8s-xxx",
	}

	addons, err := dbAccess.FindByParams(clusterAddonParams)
	assert.NoError(t, err)
	assert.Len(t, addons, 1)
	assert.Equal(t, uint64(0x1), addons[0].ID)
	assert.Equal(t, uint64(0x1), addons[0].AddonID)
	assert.Equal(t, "bcs-k8s-xxx", addons[0].K8sClusterName)
}

func TestDeleteClusterAddons(t *testing.T) {
	db, err := SetUpTestDBForClusterAddons()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterAddonsDbAccess(db)

	addon := &model.K8sClusterAddonsModel{
		AddonID:        1,
		K8sClusterName: "bcs-k8s-xxx",
	}

	_, err = dbAccess.Create(addon)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}
