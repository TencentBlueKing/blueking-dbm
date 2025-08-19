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
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sClusterConfigSample = &model.K8sClusterConfigModel{
	ClusterName:  "test-cluster",
	APIServerURL: "https://api.example.com:6443",
	RegionName:   "us-west-1",
	RegionCode:   "usw1",
	Provider:     "aws",
}

var batchK8sClusterConfigSamples = []*model.K8sClusterConfigModel{
	{
		ClusterName:  "dev-cluster",
		APIServerURL: "https://api.example.com:6443",
		RegionName:   "us-east-1",
		RegionCode:   "use1",
		Provider:     "aws",
	},
	{
		ClusterName:  "prod-cluster",
		APIServerURL: "https://api.example.com:6443",
		RegionName:   "eu-west-1",
		RegionCode:   "euw1",
		Provider:     "gcp",
	},
}

var regionQueryParamsSample = &entitys.RegionQueryParams{
	RegionName: "us-west-1",
	RegionCode: "usw1",
	Provider:   "aws",
}

type K8sClusterConfigDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sClusterConfigDbAccess
	ctx            context.Context
}

func (suite *K8sClusterConfigDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *K8sClusterConfigDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *K8sClusterConfigDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterConfig, &model.K8sClusterConfigModel{})
}

func (suite *K8sClusterConfigDbAccessTestSuite) TestCreateK8sClusterConfig() {
	t := suite.T()
	k8sClusterConfig, err := suite.dbAccess.Create(k8sClusterConfigSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterConfig.ID)
	assert.Equal(t, k8sClusterConfigSample.ClusterName, k8sClusterConfig.ClusterName)
	assert.Equal(t, k8sClusterConfigSample.APIServerURL, k8sClusterConfig.APIServerURL)
	assert.Equal(t, k8sClusterConfigSample.RegionName, k8sClusterConfig.RegionName)
	assert.Equal(t, k8sClusterConfigSample.RegionCode, k8sClusterConfig.RegionCode)
	assert.Equal(t, k8sClusterConfigSample.Provider, k8sClusterConfig.Provider)
}

func (suite *K8sClusterConfigDbAccessTestSuite) TestDeleteK8sClusterConfig() {
	t := suite.T()
	k8sClusterConfig, err := suite.dbAccess.Create(k8sClusterConfigSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterConfig.ID)

	rows, err := suite.dbAccess.DeleteByID(k8sClusterConfig.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterConfigDbAccessTestSuite) TestUpdateK8sClusterConfig() {
	t := suite.T()
	k8sClusterConfig, err := suite.dbAccess.Create(k8sClusterConfigSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterConfig.ID)

	newK8sClusterConfig := &model.K8sClusterConfigModel{
		ID:           k8sClusterConfig.ID,
		ClusterName:  "updated-cluster",
		APIServerURL: "https://api.updated.com:6443",
		RegionName:   "us-east-2",
		RegionCode:   "use2",
		Provider:     "azure",
	}
	rows, err := suite.dbAccess.Update(newK8sClusterConfig)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterConfigDbAccessTestSuite) TestGetK8sClusterConfig() {
	t := suite.T()
	k8sClusterConfig, err := suite.dbAccess.Create(k8sClusterConfigSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterConfig.ID)

	foundK8sClusterConfig, err := suite.dbAccess.FindByID(k8sClusterConfig.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundK8sClusterConfig)

	assert.Equal(t, k8sClusterConfig.ClusterName, foundK8sClusterConfig.ClusterName)
	assert.Equal(t, k8sClusterConfig.APIServerURL, foundK8sClusterConfig.APIServerURL)
	assert.Equal(t, k8sClusterConfig.RegionName, foundK8sClusterConfig.RegionName)
	assert.Equal(t, k8sClusterConfig.RegionCode, foundK8sClusterConfig.RegionCode)
	assert.Equal(t, k8sClusterConfig.Provider, foundK8sClusterConfig.Provider)
}

func (suite *K8sClusterConfigDbAccessTestSuite) TestFindK8sClusterCfgByClusterName() {
	t := suite.T()
	k8sClusterConfig, err := suite.dbAccess.Create(k8sClusterConfigSample)
	assert.NoError(t, err)
	assert.NotZero(t, k8sClusterConfig.ID)

	foundK8sClusterConfig, err := suite.dbAccess.FindByClusterName(k8sClusterConfig.ClusterName)
	assert.NoError(t, err)
	assert.NotNil(t, foundK8sClusterConfig)
	assert.Equal(t, k8sClusterConfig.ClusterName, foundK8sClusterConfig.ClusterName)
	assert.Equal(t, k8sClusterConfig.APIServerURL, foundK8sClusterConfig.APIServerURL)
}

func (suite *K8sClusterConfigDbAccessTestSuite) TestFindRegionsByParams() {
	t := suite.T()
	for _, sample := range batchK8sClusterConfigSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	regions, err := suite.dbAccess.FindRegionsByParams(regionQueryParamsSample)
	assert.NoError(t, err)
	assert.NotNil(t, regions)
}

func TestK8sClusterConfigDbAccessTestSt(t *testing.T) {
	suite.Run(t, new(K8sClusterConfigDbAccessTestSuite))
}
