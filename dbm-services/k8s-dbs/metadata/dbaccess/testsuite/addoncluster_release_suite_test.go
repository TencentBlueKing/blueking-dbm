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

var addonClusterReleaseSample = &models.AddonClusterReleaseModel{
	RepoName:           "test-release-repo",
	RepoRepository:     "https://www.example.com",
	ChartVersion:       "1.0.0",
	ChartName:          "mysql-cluster",
	Namespace:          "default",
	K8sClusterConfigID: 1,
	ReleaseName:        "test-release",
	ChartValues:        "{\"replicas\": 3, \"storage\": \"10Gi\"}",
}

var batchAddonClusterReleaseSamples = []*models.AddonClusterReleaseModel{
	{
		RepoName:           "redis-release-repo",
		RepoRepository:     "https://www.example.com",
		ChartVersion:       "2.0.0",
		ChartName:          "redis-cluster",
		Namespace:          "redis-ns",
		K8sClusterConfigID: 2,
		ReleaseName:        "redis-release",
		ChartValues:        "{\"replicas\": 5, \"storage\": \"20Gi\"}",
	},
	{
		RepoName:           "mongodb-release-repo",
		RepoRepository:     "https://www.example.com",
		ChartVersion:       "3.0.0",
		ChartName:          "mongodb-cluster",
		Namespace:          "mongodb-ns",
		K8sClusterConfigID: 3,
		ReleaseName:        "mongodb-release",
		ChartValues:        "{\"replicas\": 7, \"storage\": \"30Gi\"}",
	},
}

type AddonClusterReleaseDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonClusterReleaseDbAccess
	ctx            context.Context
}

func (suite *AddonClusterReleaseDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbaccess.NewAddonClusterReleaseDbAccess(db)
}

func (suite *AddonClusterReleaseDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterReleaseDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonClusterRelease, &models.AddonClusterReleaseModel{})
}

func (suite *AddonClusterReleaseDbAccessTestSuite) TestCreateAddonClusterRelease() {
	t := suite.T()
	release, err := suite.dbAccess.Create(addonClusterReleaseSample)
	assert.NoError(t, err)
	assert.NotNil(t, release)
	assert.Equal(t, addonClusterReleaseSample.RepoName, release.RepoName)
	assert.Equal(t, addonClusterReleaseSample.RepoRepository, release.RepoRepository)
	assert.Equal(t, addonClusterReleaseSample.ChartVersion, release.ChartVersion)
	assert.Equal(t, addonClusterReleaseSample.ChartName, release.ChartName)
	assert.Equal(t, addonClusterReleaseSample.Namespace, release.Namespace)
	assert.Equal(t, addonClusterReleaseSample.K8sClusterConfigID, release.K8sClusterConfigID)
	assert.Equal(t, addonClusterReleaseSample.ReleaseName, release.ReleaseName)
	assert.Equal(t, addonClusterReleaseSample.ChartValues, release.ChartValues)
}

func (suite *AddonClusterReleaseDbAccessTestSuite) TestGetAddonClusterRelease() {
	t := suite.T()
	release, err := suite.dbAccess.Create(addonClusterReleaseSample)
	assert.NoError(t, err)
	assert.NotZero(t, release.ID)

	foundRelease, err := suite.dbAccess.FindByID(uint64(release.ID))
	assert.NoError(t, err)
	assert.NotNil(t, foundRelease)
	assert.Equal(t, release.ID, foundRelease.ID)
	assert.Equal(t, release.RepoName, foundRelease.RepoName)
	assert.Equal(t, release.RepoRepository, foundRelease.RepoRepository)
	assert.Equal(t, release.ChartName, foundRelease.ChartName)
	assert.Equal(t, release.ChartVersion, foundRelease.ChartVersion)
	assert.Equal(t, release.Namespace, foundRelease.Namespace)
	assert.Equal(t, release.ReleaseName, foundRelease.ReleaseName)
}

func (suite *AddonClusterReleaseDbAccessTestSuite) TestFindAddonClusterReleaseByParams() {
	t := suite.T()
	release, err := suite.dbAccess.Create(addonClusterReleaseSample)
	assert.NoError(t, err)
	assert.NotZero(t, release.ID)

	params := &entitys.ClusterReleaseQueryParams{
		K8sClusterConfigID: 1,
		ReleaseName:        "test-release",
		Namespace:          "default",
	}
	foundRelease, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.NotNil(t, foundRelease)
	assert.Equal(t, release.ID, foundRelease.ID)
	assert.Equal(t, "test-release-repo", foundRelease.RepoName)
	assert.Equal(t, "mysql-cluster", foundRelease.ChartName)
	assert.Equal(t, "1.0.0", foundRelease.ChartVersion)
	assert.Equal(t, "test-release", foundRelease.ReleaseName)
	assert.Equal(t, "default", foundRelease.Namespace)
}

func (suite *AddonClusterReleaseDbAccessTestSuite) TestUpdateAddonClusterRelease() {
	t := suite.T()
	release, err := suite.dbAccess.Create(addonClusterReleaseSample)
	assert.NoError(t, err)
	assert.NotZero(t, release.ID)

	newRelease := &models.AddonClusterReleaseModel{
		ID:                 release.ID,
		RepoName:           "updated-release-repo",
		RepoRepository:     "https://www.example.com",
		ChartVersion:       "1.1.0",
		ChartName:          "updated-cluster",
		Namespace:          "updated-ns",
		K8sClusterConfigID: 2,
		ReleaseName:        "updated-release",
		ChartValues:        "{\"replicas\": 5, \"storage\": \"20Gi\"}",
	}
	rows, err := suite.dbAccess.Update(newRelease)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterReleaseDbAccessTestSuite) TestDeleteAddonClusterRelease() {
	t := suite.T()
	release, err := suite.dbAccess.Create(addonClusterReleaseSample)
	assert.NoError(t, err)
	assert.NotZero(t, release.ID)

	rows, err := suite.dbAccess.DeleteByID(uint64(release.ID))
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *AddonClusterReleaseDbAccessTestSuite) TestListAddonClusterReleaseByPage() {
	t := suite.T()
	for _, sample := range batchAddonClusterReleaseSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}
	releases, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(len(batchAddonClusterReleaseSamples)), total)
	assert.Equal(t, len(batchAddonClusterReleaseSamples), len(releases))

	releaseMap := make(map[string]models.AddonClusterReleaseModel)
	for _, release := range releases {
		releaseMap[release.ReleaseName] = release
	}

	for _, sample := range batchAddonClusterReleaseSamples {
		foundRelease, ok := releaseMap[sample.ReleaseName]
		assert.True(t, ok, "AddonClusterRelease with name %s not found", sample.ReleaseName)
		assert.Equal(t, sample.RepoName, foundRelease.RepoName)
		assert.Equal(t, sample.ChartName, foundRelease.ChartName)
		assert.Equal(t, sample.ChartVersion, foundRelease.ChartVersion)
		assert.Equal(t, sample.Namespace, foundRelease.Namespace)
	}
}

func TestAddonClusterReleaseDbAccess(t *testing.T) {
	suite.Run(t, new(AddonClusterReleaseDbAccessTestSuite))
}
