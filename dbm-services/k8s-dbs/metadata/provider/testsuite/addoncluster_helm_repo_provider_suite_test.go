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
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonClusterHelmRepoEntity = &metaenitty.AddonClusterHelmRepoEntity{
	RepoName:       "repo_name_01",
	RepoRepository: "repo_repository_01",
	RepoUsername:   "repo_username_01",
	RepoPassword:   "repo_password_01",
	ChartName:      "chart_name_01",
	ChartVersion:   "chart_version_01",
}

var addonClusterHelmRepoEntityList = []*metaenitty.AddonClusterHelmRepoEntity{
	{
		RepoName:       "repo_name_01",
		RepoRepository: "repo_repository_01",
		RepoUsername:   "repo_username_01",
		RepoPassword:   "repo_password_01",
		ChartName:      "chart_name_01",
		ChartVersion:   "chart_version_01",
	},
	{
		RepoName:       "repo_name_02",
		RepoRepository: "repo_repository_02",
		RepoUsername:   "repo_username_02",
		RepoPassword:   "repo_password_02",
		ChartName:      "chart_name_02",
		ChartVersion:   "chart_version_02",
	},
}

type AddonClusterHelmRepoProviderTestSuite struct {
	suite.Suite
	mySqlContainer               *testhelper.MySQLContainerWrapper
	addonClusterHelmRepoProvider provider.AddonClusterHelmRepoProvider
	ctx                          context.Context
}

func (suite *AddonClusterHelmRepoProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	suite.addonClusterHelmRepoProvider = provider.NewAddonClusterHelmRepoProvider(dbAccess)
}

func (suite *AddonClusterHelmRepoProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterHelmRepoProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonClusterHelmRepo, &model.AddonClusterHelmRepoModel{})
}

func TestAddonClusterHelmRepoProvider(t *testing.T) {
	suite.Run(t, new(AddonClusterHelmRepoProviderTestSuite))
}

func (suite *AddonClusterHelmRepoProviderTestSuite) TestCreateHelmRepo() {
	t := suite.T()
	addedEntity, err := suite.addonClusterHelmRepoProvider.CreateHelmRepo(dbsCtx, addonClusterHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)
	assert.Equal(t, addonClusterHelmRepoEntity.RepoName, addedEntity.RepoName)
	assert.Equal(t, addonClusterHelmRepoEntity.RepoRepository, addedEntity.RepoRepository)
	assert.Equal(t, addonClusterHelmRepoEntity.RepoUsername, addedEntity.RepoUsername)
	assert.Equal(t, addonClusterHelmRepoEntity.RepoPassword, addedEntity.RepoPassword)
	assert.Equal(t, addonClusterHelmRepoEntity.ChartName, addedEntity.ChartName)
	assert.Equal(t, addonClusterHelmRepoEntity.ChartVersion, addedEntity.ChartVersion)
}

func (suite *AddonClusterHelmRepoProviderTestSuite) TestDeleteHelmRepoByID() {
	t := suite.T()
	addedEntity, err := suite.addonClusterHelmRepoProvider.CreateHelmRepo(dbsCtx, addonClusterHelmRepoEntity)
	assert.NoError(t, err)

	rows, err := suite.addonClusterHelmRepoProvider.DeleteHelmRepoByID(uint64(addedEntity.ID))
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterHelmRepoProviderTestSuite) TestFindHelmRepoByID() {
	t := suite.T()
	addedEntity, err := suite.addonClusterHelmRepoProvider.CreateHelmRepo(dbsCtx, addonClusterHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	foundEntity, err := suite.addonClusterHelmRepoProvider.FindHelmRepoByID(uint64(addedEntity.ID))
	assert.NoError(t, err)
	assert.NotNil(t, foundEntity)
	assert.Equal(t, addedEntity.ID, foundEntity.ID)
	assert.Equal(t, addedEntity.RepoName, foundEntity.RepoName)
	assert.Equal(t, addedEntity.RepoRepository, foundEntity.RepoRepository)
	assert.Equal(t, addedEntity.RepoUsername, foundEntity.RepoUsername)
	assert.Equal(t, addedEntity.RepoPassword, foundEntity.RepoPassword)
	assert.Equal(t, addedEntity.ChartName, foundEntity.ChartName)
	assert.Equal(t, addedEntity.ChartVersion, foundEntity.ChartVersion)
}

func (suite *AddonClusterHelmRepoProviderTestSuite) TestFindByParams() {
	t := suite.T()
	for _, entity := range addonClusterHelmRepoEntityList {
		result, err := suite.addonClusterHelmRepoProvider.CreateHelmRepo(dbsCtx, entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	params := &metaenitty.HelmRepoQueryParams{
		RepoName: "repo_name_01",
	}
	foundEntity, err := suite.addonClusterHelmRepoProvider.FindByParams(params)
	assert.NoError(t, err)
	assert.NotNil(t, foundEntity)
	assert.Equal(t, addonClusterHelmRepoEntityList[0].RepoName, foundEntity.RepoName)
}

func (suite *AddonClusterHelmRepoProviderTestSuite) TestUpdateHelmRepo() {
	t := suite.T()
	addedEntity, err := suite.addonClusterHelmRepoProvider.CreateHelmRepo(dbsCtx, addonClusterHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotZero(t, addedEntity.ID)

	addedEntity.RepoName = "updated_repo_name"
	rows, err := suite.addonClusterHelmRepoProvider.UpdateHelmRepo(addedEntity)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterHelmRepoProviderTestSuite) TestListHelmRepos() {
	t := suite.T()
	for _, entity := range addonClusterHelmRepoEntityList {
		result, err := suite.addonClusterHelmRepoProvider.CreateHelmRepo(dbsCtx, entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}

	helmRepos, err := suite.addonClusterHelmRepoProvider.ListHelmRepos(pagin)
	assert.NoError(t, err)

	addonNames := make(map[string]bool)
	for _, addon := range helmRepos {
		addonNames[addon.RepoName] = true
	}

	for _, addon := range addonClusterHelmRepoEntityList {
		assert.True(t, addonNames[addon.RepoName], addon.RepoName)
	}
}
