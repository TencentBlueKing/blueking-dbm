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
	models "k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonClusterHelmRepoSample = &models.AddonClusterHelmRepoModel{
	RepoName:       "test-cluster-repo",
	RepoRepository: "https://www.example.com",
	RepoUsername:   "clusteruser",
	RepoPassword:   "clusterpass",
	ChartName:      "mysql-cluster",
	ChartVersion:   "1.0.0",
}

var batchAddonClusterHelmRepoSamples = []*models.AddonClusterHelmRepoModel{
	{
		RepoName:       "redis-cluster-repo",
		RepoRepository: "https://www.example.com",
		RepoUsername:   "redisclusteruser",
		RepoPassword:   "redisclusterpass",
		ChartName:      "redis-cluster",
		ChartVersion:   "2.0.0",
	},
	{
		RepoName:       "mongodb-cluster-repo",
		RepoRepository: "https://www.example.com",
		RepoUsername:   "mongoclusteruser",
		RepoPassword:   "mongoclusterpass",
		ChartName:      "mongodb-cluster",
		ChartVersion:   "3.0.0",
	},
}

type AddonClusterHelmRepoDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonClusterHelmRepoDbAccess
	ctx            context.Context
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbaccess.NewAddonClusterHelmRepoDbAccess(db)
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonClusterHelmRepo, &models.AddonClusterHelmRepoModel{})
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) TestCreateAddonClusterHelmRepo() {
	t := suite.T()
	repo, err := suite.dbAccess.Create(addonClusterHelmRepoSample)
	assert.NoError(t, err)
	assert.NotZero(t, repo.ID)
	assert.Equal(t, addonClusterHelmRepoSample.RepoName, repo.RepoName)
	assert.Equal(t, addonClusterHelmRepoSample.RepoRepository, repo.RepoRepository)
	assert.Equal(t, addonClusterHelmRepoSample.RepoUsername, repo.RepoUsername)
	assert.Equal(t, addonClusterHelmRepoSample.RepoPassword, repo.RepoPassword)
	assert.Equal(t, addonClusterHelmRepoSample.ChartName, repo.ChartName)
	assert.Equal(t, addonClusterHelmRepoSample.ChartVersion, repo.ChartVersion)
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) TestGetAddonClusterHelmRepo() {
	t := suite.T()
	repo, err := suite.dbAccess.Create(addonClusterHelmRepoSample)
	assert.NoError(t, err)
	assert.NotZero(t, repo.ID)

	foundRepo, err := suite.dbAccess.FindByID(uint64(repo.ID))
	assert.NoError(t, err)
	assert.NotNil(t, foundRepo)
	assert.Equal(t, repo.ID, foundRepo.ID)
	assert.Equal(t, repo.RepoName, foundRepo.RepoName)
	assert.Equal(t, repo.RepoRepository, foundRepo.RepoRepository)
	assert.Equal(t, repo.ChartName, foundRepo.ChartName)
	assert.Equal(t, repo.ChartVersion, foundRepo.ChartVersion)
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) TestFindClusterHelmRepoByParams() {
	t := suite.T()
	repo, err := suite.dbAccess.Create(addonClusterHelmRepoSample)
	assert.NoError(t, err)
	assert.NotZero(t, repo.ID)

	params := &entitys.HelmRepoQueryParams{
		RepoName:     "test-cluster-repo",
		ChartName:    "mysql-cluster",
		ChartVersion: "1.0.0",
	}
	foundRepo, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.NotNil(t, foundRepo)
	assert.Equal(t, repo.ID, foundRepo.ID)
	assert.Equal(t, "test-cluster-repo", foundRepo.RepoName)
	assert.Equal(t, "mysql-cluster", foundRepo.ChartName)
	assert.Equal(t, "1.0.0", foundRepo.ChartVersion)
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) TestUpdateAddonClusterHelmRepo() {
	t := suite.T()
	createdRepo, err := suite.dbAccess.Create(addonClusterHelmRepoSample)
	assert.NoError(t, err)
	assert.NotZero(t, createdRepo.ID)

	newRepo := &models.AddonClusterHelmRepoModel{
		ID:             createdRepo.ID,
		RepoName:       "updated-cluster-repo",
		RepoRepository: "https://www.example.com",
		RepoUsername:   "updatedclusteruser",
		RepoPassword:   "updatedclusterpass",
		ChartName:      "updated-cluster-chart",
		ChartVersion:   "1.1.0",
	}
	rows, err := suite.dbAccess.Update(newRepo)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) TestDeleteAddonClusterHelmRepo() {
	t := suite.T()
	createdRepo, err := suite.dbAccess.Create(addonClusterHelmRepoSample)
	assert.NoError(t, err)
	assert.NotZero(t, createdRepo.ID)

	rows, err := suite.dbAccess.DeleteByID(uint64(createdRepo.ID))
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterHelmRepoDbAccessTestSuite) TestListAddonClusterHelmRepoByPage() {
	t := suite.T()
	for _, sample := range batchAddonClusterHelmRepoSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}
	repos, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(len(batchAddonClusterHelmRepoSamples)), total)
	assert.Equal(t, len(batchAddonClusterHelmRepoSamples), len(repos))

	repoMap := make(map[string]models.AddonClusterHelmRepoModel)
	for _, repo := range repos {
		repoMap[repo.RepoName] = repo
	}

	for _, sample := range batchAddonClusterHelmRepoSamples {
		foundRepo, ok := repoMap[sample.RepoName]
		assert.True(t, ok, "AddonClusterHelmRepo with name %s not found", sample.RepoName)
		assert.Equal(t, sample.RepoRepository, foundRepo.RepoRepository)
		assert.Equal(t, sample.ChartName, foundRepo.ChartName)
		assert.Equal(t, sample.ChartVersion, foundRepo.ChartVersion)
	}
}

func TestAddonClusterHelmRepoDbAccess(t *testing.T) {
	suite.Run(t, new(AddonClusterHelmRepoDbAccessTestSuite))
}
