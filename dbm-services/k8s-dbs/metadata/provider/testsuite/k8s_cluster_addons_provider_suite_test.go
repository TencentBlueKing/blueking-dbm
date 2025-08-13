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

package testsuite

import (
	"context"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sClusterAddonsEntity = &metaenitty.K8sClusterAddonsEntity{
	AddonID:        uint64(1),
	K8sClusterName: "k8s_cluster_name_01",
}

var k8sClusterAddonsEntityList = []metaenitty.K8sClusterAddonsEntity{
	{
		AddonID:        uint64(1),
		K8sClusterName: "k8s_cluster_name_01",
	},
	{
		AddonID:        uint64(2),
		K8sClusterName: "k8s_cluster_name_02",
	},
}

type K8sClusterAddonsProviderTestSuite struct {
	suite.Suite
	mySqlContainer  *testhelper.MySQLContainerWrapper
	clusterProvider provider.K8sClusterAddonsProvider
	storageProvider provider.K8sCrdStorageAddonProvider
	ctx             context.Context
}

func (suite *K8sClusterAddonsProviderTestSuite) SetupSuite() {
	suite.ctx = context.Background()
	mySqlContainer, err := testhelper.NewMySQLContainerWrapper(suite.ctx)
	if err != nil {
		log.Fatal(err)
	}
	suite.mySqlContainer = mySqlContainer
	db, err := testhelper.InitDBConnection(mySqlContainer.ConnStr)
	if err != nil {
		log.Fatal(err)
	}
	dbAccess := dbaccess.NewK8sClusterAddonsDbAccess(db)
	storageAddonDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterProvider := provider.NewK8sClusterAddonsProvider(dbAccess, storageAddonDbAccess)
	storageAddonProvider := provider.NewK8sCrdStorageAddonProvider(storageAddonDbAccess)
	suite.clusterProvider = clusterProvider
	suite.storageProvider = storageAddonProvider

}

func (suite *K8sClusterAddonsProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *K8sClusterAddonsProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterAddons, &model.K8sClusterAddonsModel{})
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdStorageAddon, &model.K8sCrdStorageAddonModel{})
}

func TestK8sClusterAddonsProvider(t *testing.T) {
	suite.Run(t, new(K8sClusterAddonsProviderTestSuite))
}

func (suite *K8sClusterAddonsProviderTestSuite) TestCreateClusterAddon() {
	t := suite.T()
	_, err := suite.storageProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	addonEntity, err := suite.clusterProvider.CreateClusterAddon(k8sClusterAddonsEntity)
	assert.NoError(t, err)
	assert.Equal(t, k8sClusterAddonsEntity.AddonID, addonEntity.AddonID)
	assert.Equal(t, k8sClusterAddonsEntity.K8sClusterName, addonEntity.K8sClusterName)
}

func (suite *K8sClusterAddonsProviderTestSuite) TestDeleteClusterAddon() {
	t := suite.T()
	_, err := suite.storageProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	addonEntity, err := suite.clusterProvider.CreateClusterAddon(k8sClusterAddonsEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addonEntity.ID)

	rows, err := suite.clusterProvider.DeleteClusterAddon(addonEntity.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterAddonsProviderTestSuite) TestFindClusterAddonByID() {
	t := suite.T()
	_, err := suite.storageProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)
	addonEntity, err := suite.clusterProvider.CreateClusterAddon(k8sClusterAddonsEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addonEntity.ID)

	foundAddon, err := suite.clusterProvider.FindClusterAddonByID(addonEntity.ID)
	assert.NoError(t, err)
	assert.Equal(t, addonEntity.AddonID, foundAddon.AddonID)
	assert.Equal(t, addonEntity.K8sClusterName, foundAddon.K8sClusterName)
}

func (suite *K8sClusterAddonsProviderTestSuite) TestUpdateClusterAddon() {
	t := suite.T()
	_, err := suite.storageProvider.CreateStorageAddon(addonDbsContext, k8sCrdStorageAddonEntity)
	assert.NoError(t, err)

	addonEntity, err := suite.clusterProvider.CreateClusterAddon(k8sClusterAddonsEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addonEntity.ID)

	addonEntity.K8sClusterName = "updated_k8s_cluster_name"
	rows, err := suite.clusterProvider.UpdateClusterAddon(addonEntity)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterAddonsProviderTestSuite) TestFindClusterAddonByParams() {
	t := suite.T()
	for _, entity := range k8sCrdStorageAddonEntityList {
		result, err := suite.storageProvider.CreateStorageAddon(addonDbsContext, &entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	for _, entity := range k8sClusterAddonsEntityList {
		addonEntity, err := suite.clusterProvider.CreateClusterAddon(&entity)
		assert.NoError(t, err)
		assert.NotZero(t, addonEntity.ID)
	}

	params := metaenitty.K8sClusterAddonQueryParams{
		K8sClusterName: "k8s_cluster_name_01",
	}

	addonList, err := suite.clusterProvider.FindClusterAddonByParams(&params)
	assert.NoError(t, err)

	assert.Equal(t, addonList[0].K8sClusterName, "k8s_cluster_name_01")
}
