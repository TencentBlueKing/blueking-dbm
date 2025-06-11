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

func SetUpTestDBForCd() (*gorm.DB, error) {
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
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             true,
		Description:        "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created componentVersion %+v\n", addedCd)

	var foundCd model.K8sCrdClusterDefinitionModel
	err = db.First(&foundCd, "cd_name=?", "cd1").Error
	assert.NoError(t, err, "Failed to query clusterDefinition")
	assert.Equal(t, cd.CdName, foundCd.CdName)
	assert.Equal(t, cd.AddonID, foundCd.AddonID)
	assert.Equal(t, cd.RecommendedVersion, foundCd.RecommendedVersion)
	assert.Equal(t, cd.Topologies, foundCd.Topologies)
	assert.Equal(t, cd.Releases, foundCd.Releases)
	assert.Equal(t, cd.Active, foundCd.Active)
}

func TestDeleteClusterDefinition(t *testing.T) {
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             true,
		Description:        "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created componentVersion %+v\n", addedCd)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err, "Failed to delete clusterDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateClusterDefinition(t *testing.T) {
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             true,
		Description:        "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created componentVersion %+v\n", addedCd)

	updatedCd := &model.K8sCrdClusterDefinitionModel{
		ID:                 1,
		CdName:             "cd2",
		AddonID:            uint64(1),
		RecommendedVersion: "2.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             false,
		Description:        "desc",
		UpdatedAt:          time.Now(),
	}
	rows, err := dbAccess.Update(updatedCd)
	assert.NoError(t, err, "Failed to update clusterDefinition")
	assert.Equal(t, uint64(1), rows)
}

func TestGetClusterDefinition(t *testing.T) {
	db, err := SetUpTestDBForCd()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)

	cd := &model.K8sCrdClusterDefinitionModel{
		CdName:             "cd1",
		AddonID:            uint64(1),
		RecommendedVersion: "1.0.0",
		Topologies:         "[{\"name\":\"cluster\",\"default\":true,\"components\":[{\"name\":\"vminsert\"},{\"name\":\"vmselect\"},{\"name\":\"vmstorage\"}]},{\"name\":\"select\",\"default\":false,\"vmselect-1.0.0\",\"name\":\"vmselect\"}]}]",
		Releases:           "[{\"name\":\"vmstorage-1.93.10\",\"serviceVersion\":\"1.93.10\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.93.10-cluster\"}},{\"name\":\"vmstorage-1.115.0\",\"serviceVersion\":\"1.115.0\",\"images\":{\"vmstorage\":\"victoriametrics/vmstorage:v1.115.0-cluster\"}}]",
		Active:             true,
		Description:        "desc",
	}

	addedCd, err := dbAccess.Create(cd)
	assert.NoError(t, err, "Failed to create clusterDefinition")
	fmt.Printf("Created clusterDefinition %+v\n", addedCd)

	foundCd, err := dbAccess.FindByID(1)
	assert.NoError(t, err, "Failed to find clusterDefinition")
	assert.Equal(t, cd.CdName, foundCd.CdName)
	assert.Equal(t, cd.AddonID, foundCd.AddonID)
	assert.Equal(t, cd.RecommendedVersion, foundCd.RecommendedVersion)
	assert.Equal(t, cd.Topologies, foundCd.Topologies)
	assert.Equal(t, cd.Releases, foundCd.Releases)
	assert.Equal(t, cd.Active, foundCd.Active)
}
