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
	"k8s-dbs/common/entity"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonHelmRepoSample = &model.AddonHelmRepoModel{
	RepoName:       "test-repo",
	RepoRepository: "https://www.example.com",
	RepoUsername:   "testuser",
	RepoPassword:   "testpass",
	ChartName:      "mysql",
	ChartVersion:   "1.0.0",
}

var batchAddonHelmRepoSamples = []*model.AddonHelmRepoModel{
	{
		RepoName:       "redis-repo",
		RepoRepository: "https://www.example.com",
		RepoUsername:   "redisuser",
		RepoPassword:   "redispass",
		ChartName:      "redis",
		ChartVersion:   "2.0.0",
	},
	{
		RepoName:       "mongodb-repo",
		RepoRepository: "https://www.example.com",
		RepoUsername:   "mongouser",
		RepoPassword:   "mongopass",
		ChartName:      "mongodb",
		ChartVersion:   "3.0.0",
	},
}

type AddonHelmRepoDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonHelmRepoDbAccess
	ctx            context.Context
}

func (suite *AddonHelmRepoDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbaccess.NewAddonHelmRepoDbAccess(db)
}

func (suite *AddonHelmRepoDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonHelmRepoDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonHelmRepo, &model.AddonHelmRepoModel{})
}

func (suite *AddonHelmRepoDbAccessTestSuite) TestCreateAddonHelmRepo() {
	t := suite.T()
	createdRepo, err := suite.dbAccess.Create(addonHelmRepoSample)
	assert.NoError(t, err)
	assert.NotNil(t, createdRepo)
	assert.Equal(t, createdRepo.RepoName, addonHelmRepoSample.RepoName)
	assert.Equal(t, createdRepo.RepoRepository, addonHelmRepoSample.RepoRepository)
	assert.Equal(t, createdRepo.RepoUsername, addonHelmRepoSample.RepoUsername)
	assert.Equal(t, createdRepo.RepoPassword, addonHelmRepoSample.RepoPassword)
	assert.Equal(t, createdRepo.ChartName, addonHelmRepoSample.ChartName)
	assert.Equal(t, createdRepo.ChartVersion, addonHelmRepoSample.ChartVersion)
}

func (suite *AddonHelmRepoDbAccessTestSuite) TestGetAddonHelmRepo() {
	t := suite.T()
	createdRepo, err := suite.dbAccess.Create(addonHelmRepoSample)
	assert.NoError(t, err)
	assert.NotNil(t, createdRepo)

	foundRepo, err := suite.dbAccess.FindByID(uint64(createdRepo.ID))
	assert.NoError(t, err)
	assert.NotNil(t, foundRepo)
	assert.Equal(t, createdRepo.ID, foundRepo.ID)
	assert.Equal(t, createdRepo.RepoName, foundRepo.RepoName)
	assert.Equal(t, createdRepo.RepoRepository, foundRepo.RepoRepository)
	assert.Equal(t, createdRepo.ChartName, foundRepo.ChartName)
	assert.Equal(t, createdRepo.ChartVersion, foundRepo.ChartVersion)
}

func (suite *AddonHelmRepoDbAccessTestSuite) TestFindAddonHelmRepoByParams() {
	t := suite.T()
	foundRepo, err := suite.dbAccess.Create(addonHelmRepoSample)
	assert.NoError(t, err)
	assert.NotNil(t, foundRepo)

	params := &entitys.HelmRepoQueryParams{
		RepoName:     "test-repo",
		ChartName:    "mysql",
		ChartVersion: "1.0.0",
	}
	repo, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.NotNil(t, repo)
	assert.Equal(t, repo.ID, foundRepo.ID)
	assert.Equal(t, repo.RepoName, params.RepoName)
	assert.Equal(t, repo.ChartName, params.ChartName)
	assert.Equal(t, repo.ChartVersion, params.ChartVersion)
}

func (suite *AddonHelmRepoDbAccessTestSuite) TestUpdateAddonHelmRepo() {
	t := suite.T()
	repo, err := suite.dbAccess.Create(addonHelmRepoSample)
	assert.NoError(t, err)
	assert.NotZero(t, repo.ID)

	newRepo := &model.AddonHelmRepoModel{
		ID:             repo.ID,
		RepoName:       "updated-repo",
		RepoRepository: "https://www.example.com",
		RepoUsername:   "updateduser",
		RepoPassword:   "updatedpass",
		ChartName:      "updated-chart",
		ChartVersion:   "1.1.0",
	}
	rows, err := suite.dbAccess.Update(newRepo)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonHelmRepoDbAccessTestSuite) TestDeleteAddonHelmRepo() {
	t := suite.T()
	repo, err := suite.dbAccess.Create(addonHelmRepoSample)
	assert.NoError(t, err)
	assert.NotZero(t, repo.ID)

	rows, err := suite.dbAccess.DeleteByID(uint64(repo.ID))
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonHelmRepoDbAccessTestSuite) TestListAddonHelmReposByPage() {
	t := suite.T()
	for _, sample := range batchAddonHelmRepoSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}
	repos, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, len(batchAddonHelmRepoSamples), len(repos))
	assert.Equal(t, int64(len(batchAddonHelmRepoSamples)), total)

	repoMap := make(map[string]model.AddonHelmRepoModel)
	for _, repo := range repos {
		repoMap[repo.RepoName] = repo
	}

	for _, sample := range batchAddonHelmRepoSamples {
		foundRepo, ok := repoMap[sample.RepoName]
		assert.True(t, ok, "Repo with name %s not found", sample.RepoName)
		assert.Equal(t, sample.RepoName, foundRepo.RepoName)
		assert.Equal(t, sample.RepoRepository, foundRepo.RepoRepository)
		assert.Equal(t, sample.RepoUsername, foundRepo.RepoUsername)
		assert.Equal(t, sample.RepoPassword, foundRepo.RepoPassword)
		assert.Equal(t, sample.ChartName, foundRepo.ChartName)
		assert.Equal(t, sample.ChartVersion, foundRepo.ChartVersion)
	}
}

func TestAddonHelmRepoDbAccessTestSuite(t *testing.T) {
	suite.Run(t, new(AddonHelmRepoDbAccessTestSuite))
}
