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

	"github.com/jinzhu/copier"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonHelmRepoEntity = &metaenitty.AddonHelmRepoEntity{
	RepoName:       "repo_name_1",
	RepoRepository: "repo_repository_1",
	RepoUsername:   "repo_username_1",
	RepoPassword:   "repo_password_1",
	ChartName:      "chart_name_1",
	ChartVersion:   "chart_version_1",
}

var addonHelmRepoEntityList = []metaenitty.AddonHelmRepoEntity{
	{
		RepoName:       "repo_name_1",
		RepoRepository: "repo_repository_1",
		RepoUsername:   "repo_username_1",
		RepoPassword:   "repo_password_1",
		ChartName:      "chart_name_1",
		ChartVersion:   "chart_version_1",
	},
	{
		RepoName:       "repo_name_2",
		RepoRepository: "repo_repository_2",
		RepoUsername:   "repo_username_2",
		RepoPassword:   "repo_password_2",
		ChartName:      "chart_name_2",
		ChartVersion:   "chart_version_2",
	},
}

var dbsCtx = &commentity.DbsContext{
	BkAuth: &commentity.BKAuth{
		BkUserName:  "bkuser",
		BkAppCode:   "bkappcode",
		BkAppSecret: "bkappsecret",
	},
}

type AddonHelmRepoProviderTestSuite struct {
	suite.Suite
	mySqlContainer        *testhelper.MySQLContainerWrapper
	addonHelmRepoProvider provider.AddonHelmRepoProvider
	ctx                   context.Context
}

func (suite *AddonHelmRepoProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonHelmRepoDbAccess(db)
	addonHelmRepoProvider := provider.NewAddonHelmRepoProvider(dbAccess)
	suite.addonHelmRepoProvider = addonHelmRepoProvider
}

func (suite *AddonHelmRepoProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonHelmRepoProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonHelmRepo, &model.AddonHelmRepoModel{})
}

func TestAddonHelmRepoProvider(t *testing.T) {
	suite.Run(t, new(AddonHelmRepoProviderTestSuite))
}

func (suite *AddonHelmRepoProviderTestSuite) TestCreateHelmRepo() {
	t := suite.T()
	repo, err := suite.addonHelmRepoProvider.CreateHelmRepo(dbsCtx, addonHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotNil(t, repo.ID)
	assert.Equal(t, addonHelmRepoEntity.RepoName, repo.RepoName)
	assert.Equal(t, addonHelmRepoEntity.RepoRepository, repo.RepoRepository)
	assert.Equal(t, addonHelmRepoEntity.RepoUsername, repo.RepoUsername)
	assert.Equal(t, addonHelmRepoEntity.RepoPassword, repo.RepoPassword)
}

func (suite *AddonHelmRepoProviderTestSuite) TestDeleteHelmRepoByID() {
	t := suite.T()
	repo, err := suite.addonHelmRepoProvider.CreateHelmRepo(dbsCtx, addonHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotNil(t, repo.ID)

	rows, err := suite.addonHelmRepoProvider.DeleteHelmRepoByID(uint64(repo.ID))
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

}

func (suite *AddonHelmRepoProviderTestSuite) TestFindHelmRepoByID() {
	t := suite.T()
	repo, err := suite.addonHelmRepoProvider.CreateHelmRepo(dbsCtx, addonHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotNil(t, repo.ID)

	entity, err := suite.addonHelmRepoProvider.FindHelmRepoByID(uint64(repo.ID))
	assert.NoError(t, err)
	assert.Equal(t, addonHelmRepoEntity.RepoName, entity.RepoName)
	assert.Equal(t, addonHelmRepoEntity.RepoRepository, entity.RepoRepository)
	assert.Equal(t, addonHelmRepoEntity.RepoUsername, entity.RepoUsername)
	assert.Equal(t, addonHelmRepoEntity.RepoPassword, entity.RepoPassword)
}

func (suite *AddonHelmRepoProviderTestSuite) TestFindByParams() {
	t := suite.T()
	repo, err := suite.addonHelmRepoProvider.CreateHelmRepo(dbsCtx, addonHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotNil(t, repo.ID)

	var params = metaenitty.HelmRepoQueryParams{}
	err = copier.Copy(&params, repo)
	assert.NoError(t, err)

	repoEntity, err := suite.addonHelmRepoProvider.FindByParams(&params)
	assert.NoError(t, err)
	assert.Equal(t, repo.RepoName, repoEntity.RepoName)
	assert.Equal(t, repo.RepoRepository, repoEntity.RepoRepository)
	assert.Equal(t, repo.RepoUsername, repoEntity.RepoUsername)
	assert.Equal(t, repo.RepoPassword, repoEntity.RepoPassword)
}

func (suite *AddonHelmRepoProviderTestSuite) TestUpdateHelmRepo() {
	t := suite.T()
	repo, err := suite.addonHelmRepoProvider.CreateHelmRepo(dbsCtx, addonHelmRepoEntity)
	assert.NoError(t, err)
	assert.NotNil(t, repo.ID)

	repo.ChartName = "update_02"

	rows, err := suite.addonHelmRepoProvider.UpdateHelmRepo(repo)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

}

func (suite *AddonHelmRepoProviderTestSuite) TestListHelmRepos() {
	t := suite.T()
	for _, repo := range addonHelmRepoEntityList {
		helmRepo, err := suite.addonHelmRepoProvider.CreateHelmRepo(dbsCtx, &repo)
		assert.NoError(t, err)
		assert.NotNil(t, helmRepo.ID)
	}

	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}

	repos, err := suite.addonHelmRepoProvider.ListHelmRepos(pagin)
	assert.NoError(t, err)
	assert.Equal(t, len(addonHelmRepoEntityList), len(repos))

	addonHelmRepoNames := make(map[string]bool)
	for _, addon := range repos {
		addonHelmRepoNames[addon.RepoName] = true
	}

	for _, addon := range addonHelmRepoEntityList {
		assert.True(t, addonHelmRepoNames[addon.RepoName], addon.RepoName)
	}
}
