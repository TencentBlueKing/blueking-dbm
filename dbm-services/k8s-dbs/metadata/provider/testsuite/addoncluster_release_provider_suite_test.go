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
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonClusterReleaseEntity = &metaentity.AddonClusterReleaseEntity{
	RepoName:           "repo_name_01",
	RepoRepository:     "repo_repository_01",
	ChartVersion:       "chart_version_01",
	ChartName:          "chart_name_01",
	Namespace:          "namespace_01",
	K8sClusterConfigID: uint64(1),
	ReleaseName:        "release_name_01",
	ChartValues:        "chart_values_01",
}

var addonClusterReleaseEntityList = []*metaentity.AddonClusterReleaseEntity{
	{
		RepoName:           "repo_name_01",
		RepoRepository:     "repo_repository_01",
		ChartVersion:       "chart_version_01",
		ChartName:          "chart_name_01",
		Namespace:          "namespace_01",
		K8sClusterConfigID: uint64(1),
		ReleaseName:        "release_name_01",
		ChartValues:        "chart_values_01",
	},
	{
		RepoName:           "repo_name_02",
		RepoRepository:     "repo_repository_02",
		ChartVersion:       "chart_version_02",
		ChartName:          "chart_name_02",
		Namespace:          "namespace_02",
		K8sClusterConfigID: uint64(2),
		ReleaseName:        "release_name_02",
		ChartValues:        "chart_values_02",
	},
}

type AddonClusterReleaseProviderTestSuite struct {
	suite.Suite
	mySqlContainer              *testhelper.MySQLContainerWrapper
	addonClusterReleaseProvider provider.AddonClusterReleaseProvider
	ctx                         context.Context
}

func (suite *AddonClusterReleaseProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	suite.addonClusterReleaseProvider = provider.NewAddonClusterReleaseProvider(dbAccess)
}

func (suite *AddonClusterReleaseProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterReleaseProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonClusterRelease, &model.AddonClusterReleaseModel{})
}

func TestAddonClusterReleaseProvider(t *testing.T) {
	suite.Run(t, new(AddonClusterReleaseProviderTestSuite))
}

func (suite *AddonClusterReleaseProviderTestSuite) TestCreateClusterRelease() {
	t := suite.T()
	addedEntity, err := suite.addonClusterReleaseProvider.CreateClusterRelease(addonClusterReleaseEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)
	assert.Equal(t, addonClusterReleaseEntity.RepoName, addedEntity.RepoName)
	assert.Equal(t, addonClusterReleaseEntity.RepoRepository, addedEntity.RepoRepository)
	assert.Equal(t, addonClusterReleaseEntity.ChartVersion, addedEntity.ChartVersion)
	assert.Equal(t, addonClusterReleaseEntity.ChartName, addedEntity.ChartName)
	assert.Equal(t, addonClusterReleaseEntity.Namespace, addedEntity.Namespace)
	assert.Equal(t, addonClusterReleaseEntity.K8sClusterConfigID, addedEntity.K8sClusterConfigID)
	assert.Equal(t, addonClusterReleaseEntity.ReleaseName, addedEntity.ReleaseName)
	assert.Equal(t, addonClusterReleaseEntity.ChartValues, addedEntity.ChartValues)
}

func (suite *AddonClusterReleaseProviderTestSuite) TestDeleteClusterReleaseByID() {
	t := suite.T()
	addedEntity, err := suite.addonClusterReleaseProvider.CreateClusterRelease(addonClusterReleaseEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	rows, err := suite.addonClusterReleaseProvider.DeleteClusterReleaseByID(addedEntity.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterReleaseProviderTestSuite) TestFindClusterReleaseByID() {
	t := suite.T()
	addedEntity, err := suite.addonClusterReleaseProvider.CreateClusterRelease(addonClusterReleaseEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	foundEntity, err := suite.addonClusterReleaseProvider.FindClusterReleaseByID(addedEntity.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundEntity)
	assert.Equal(t, addedEntity.ID, foundEntity.ID)
	assert.Equal(t, addedEntity.RepoName, foundEntity.RepoName)
	assert.Equal(t, addedEntity.RepoRepository, foundEntity.RepoRepository)
	assert.Equal(t, addedEntity.ChartVersion, foundEntity.ChartVersion)
	assert.Equal(t, addedEntity.ChartName, foundEntity.ChartName)
	assert.Equal(t, addedEntity.Namespace, foundEntity.Namespace)
	assert.Equal(t, addedEntity.K8sClusterConfigID, foundEntity.K8sClusterConfigID)
	assert.Equal(t, addedEntity.ReleaseName, foundEntity.ReleaseName)
	assert.Equal(t, addedEntity.ChartValues, foundEntity.ChartValues)
}

func (suite *AddonClusterReleaseProviderTestSuite) TestFindByParams() {
	t := suite.T()
	for _, entity := range addonClusterReleaseEntityList {
		result, err := suite.addonClusterReleaseProvider.CreateClusterRelease(entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	queryParams := &metaentity.ClusterReleaseQueryParams{
		RepoName: "repo_name_01",
	}
	foundEntity, err := suite.addonClusterReleaseProvider.FindByParams(queryParams)
	assert.NoError(t, err)
	assert.NotNil(t, foundEntity)
	assert.Equal(t, addonClusterReleaseEntityList[0].RepoName, foundEntity.RepoName)
}

func (suite *AddonClusterReleaseProviderTestSuite) TestUpdateClusterRelease() {
	t := suite.T()
	addedEntity, err := suite.addonClusterReleaseProvider.CreateClusterRelease(addonClusterReleaseEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	addedEntity.RepoName = "updated_repo_name"
	addedEntity.ChartValues = "updated_chart_values"

	rows, err := suite.addonClusterReleaseProvider.UpdateClusterRelease(addedEntity)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterReleaseProviderTestSuite) TestListClusterReleases() {
	t := suite.T()
	for _, entity := range addonClusterReleaseEntityList {
		result, err := suite.addonClusterReleaseProvider.CreateClusterRelease(entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}

	releases, err := suite.addonClusterReleaseProvider.ListClusterReleases(pagin)
	assert.NoError(t, err)

	addonNames := make(map[string]bool)
	for _, addon := range releases {
		addonNames[addon.RepoName] = true
	}

	for _, addon := range addonClusterReleaseEntityList {
		assert.True(t, addonNames[addon.RepoName], addon.RepoName)
	}

}
