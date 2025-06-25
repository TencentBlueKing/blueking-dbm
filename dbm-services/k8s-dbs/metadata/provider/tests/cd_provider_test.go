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

func initCdTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_clusterdefinition;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_clusterdefinition table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdClusterDefinitionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_clusterdefinition table")
		return nil, err
	}
	return db, nil
}

func TestCreateClusterDefinition(t *testing.T) {
	db, err := initCdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cdProvider := provider.NewK8sCrdClusterDefinitionProvider(dbAccess)

	cd := &entitys.K8sCrdClusterDefinitionEntity{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "{}",
		Releases:           "{}",
		Description:        "desc",
	}

	added, err := cdProvider.CreateClusterDefinition(cd)
	assert.NoError(t, err)
	assert.Equal(t, cd.CdName, added.CdName)
	assert.Equal(t, cd.AddonID, added.AddonID)
	assert.Equal(t, cd.Topologies, added.Topologies)
	assert.Equal(t, cd.Releases, added.Releases)
}

func TestDeleteClusterDefinition(t *testing.T) {
	db, err := initCdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cdProvider := provider.NewK8sCrdClusterDefinitionProvider(dbAccess)

	cd := &entitys.K8sCrdClusterDefinitionEntity{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "{}",
		Releases:           "{}",
		Active:             true,
		Description:        "desc",
	}

	_, err = cdProvider.CreateClusterDefinition(cd)
	assert.NoError(t, err)

	rows, err := cdProvider.DeleteClusterDefinitionByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateClusterDefinition(t *testing.T) {
	db, err := initCdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cdProvider := provider.NewK8sCrdClusterDefinitionProvider(dbAccess)

	cd := &entitys.K8sCrdClusterDefinitionEntity{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "{}",
		Releases:           "{}",
		Active:             true,
		Description:        "desc",
	}

	_, err = cdProvider.CreateClusterDefinition(cd)
	assert.NoError(t, err)

	updatedCd := &entitys.K8sCrdClusterDefinitionEntity{
		ID:                 1,
		CdName:             "cd2",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "{}",
		Releases:           "{}",
		Active:             false,
		Description:        "desc",
		UpdatedAt:          time.Now(),
	}
	rows, err := cdProvider.UpdateClusterDefinition(updatedCd)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetClusterDefinition(t *testing.T) {
	db, err := initCdTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cdProvider := provider.NewK8sCrdClusterDefinitionProvider(dbAccess)

	cd := &entitys.K8sCrdClusterDefinitionEntity{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "{}",
		Releases:           "{}",
		Active:             true,
		Description:        "desc",
	}

	_, err = cdProvider.CreateClusterDefinition(cd)
	assert.NoError(t, err)

	foundCd, err := cdProvider.FindClusterDefinitionByID(1)
	assert.NoError(t, err)
	assert.Equal(t, cd.CdName, foundCd.CdName)
	assert.Equal(t, cd.AddonID, foundCd.AddonID)
	assert.Equal(t, cd.Topologies, foundCd.Topologies)
	assert.Equal(t, cd.Releases, foundCd.Releases)
	assert.Equal(t, cd.Active, foundCd.Active)
}
