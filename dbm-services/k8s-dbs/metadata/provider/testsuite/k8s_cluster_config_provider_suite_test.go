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
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sClusterConfigEntity = &metaentity.K8sClusterConfigEntity{
	ClusterName:  "cluster_name_01",
	APIServerURL: "api_server_url_01",
	CACert:       "ca_cert_01",
	ClientCert:   "client_cert_01",
	ClientKey:    "client_key_01",
	Token:        "token_01",
	Username:     "username_01",
	Password:     "password_01",
	RegionEntity: reginEntity,
	Active:       true,
	Description:  "description_01",
}

var reginEntity = &metaentity.RegionEntity{
	IsPublic:    true,
	ClusterName: "cluster_name_01",
	RegionName:  "region_name_01",
	RegionCode:  "region_code_01",
	Provider:    "provider_01",
}

var k8sClusterConfigEntityList = []*metaentity.K8sClusterConfigEntity{
	{
		ClusterName:  "cluster_name_01",
		APIServerURL: "api_server_url_01",
		CACert:       "ca_cert_01",
		ClientCert:   "client_cert_01",
		ClientKey:    "client_key_01",
		Token:        "token_01",
		Username:     "username_01",
		Password:     "password_01",
		RegionEntity: reginEntity,
		Active:       true,
		Description:  "description_01",
	},
	{
		ClusterName:  "cluster_name_02",
		APIServerURL: "api_server_url_02",
		CACert:       "ca_cert_02",
		ClientCert:   "client_cert_02",
		ClientKey:    "client_key_02",
		Token:        "token_02",
		Username:     "username_02",
		Password:     "password_02",
		RegionEntity: reginEntity,
		Active:       true,
		Description:  "description_02",
	},
}

type K8sClusterConfigProviderTestSuite struct {
	suite.Suite
	mySqlContainer        *testhelper.MySQLContainerWrapper
	clusterConfigProvider provider.K8sClusterConfigProvider
	ctx                   context.Context
}

func (suite *K8sClusterConfigProviderTestSuite) SetupSuite() {
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
	clusterProvider := provider.NewK8sClusterConfigProvider(dbAccess)
	suite.clusterConfigProvider = clusterProvider
}

func (suite *K8sClusterConfigProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *K8sClusterConfigProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterConfig, &model.K8sClusterConfigModel{})
}

func TestK8sClusterConfigProvider(t *testing.T) {
	suite.Run(t, new(K8sClusterConfigProviderTestSuite))
}

func (suite *K8sClusterConfigProviderTestSuite) TestCreateConfig() {
	t := suite.T()
	clusterConfig, err := suite.clusterConfigProvider.CreateConfig(k8sClusterConfigEntity)
	assert.NoError(t, err)
	assert.NotNil(t, clusterConfig)
	assert.Equal(t, k8sClusterConfigEntity.ClusterName, clusterConfig.ClusterName)
	assert.Equal(t, k8sClusterConfigEntity.APIServerURL, clusterConfig.APIServerURL)
	assert.Equal(t, k8sClusterConfigEntity.CACert, clusterConfig.CACert)
	assert.Equal(t, k8sClusterConfigEntity.ClientCert, clusterConfig.ClientCert)
	assert.Equal(t, k8sClusterConfigEntity.ClientKey, clusterConfig.ClientKey)
	assert.Equal(t, k8sClusterConfigEntity.Token, clusterConfig.Token)
	assert.Equal(t, k8sClusterConfigEntity.Username, clusterConfig.Username)
	assert.Equal(t, k8sClusterConfigEntity.Password, clusterConfig.Password)
	assert.Equal(t, k8sClusterConfigEntity.Active, clusterConfig.Active)
	assert.Equal(t, k8sClusterConfigEntity.Description, clusterConfig.Description)
}

func (suite *K8sClusterConfigProviderTestSuite) TestDeleteConfigByID() {
	t := suite.T()
	clusterConfig, err := suite.clusterConfigProvider.CreateConfig(k8sClusterConfigEntity)
	assert.NoError(t, err)
	assert.NotNil(t, clusterConfig.ID)

	rows, err := suite.clusterConfigProvider.DeleteConfigByID(clusterConfig.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterConfigProviderTestSuite) TestFindConfigByID() {
	t := suite.T()
	clusterConfig, err := suite.clusterConfigProvider.CreateConfig(k8sClusterConfigEntity)
	assert.NoError(t, err)
	assert.NotNil(t, clusterConfig.ID)

	foundConfig, err := suite.clusterConfigProvider.FindConfigByID(clusterConfig.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundConfig)
	assert.Equal(t, clusterConfig.ID, foundConfig.ID)
	assert.Equal(t, k8sClusterConfigEntity.ClusterName, foundConfig.ClusterName)
	assert.Equal(t, k8sClusterConfigEntity.APIServerURL, foundConfig.APIServerURL)
	assert.Equal(t, k8sClusterConfigEntity.CACert, foundConfig.CACert)
	assert.Equal(t, k8sClusterConfigEntity.ClientCert, foundConfig.ClientCert)
	assert.Equal(t, k8sClusterConfigEntity.ClientKey, foundConfig.ClientKey)
	assert.Equal(t, k8sClusterConfigEntity.Token, foundConfig.Token)
	assert.Equal(t, k8sClusterConfigEntity.Username, foundConfig.Username)
	assert.Equal(t, k8sClusterConfigEntity.Password, foundConfig.Password)
	assert.Equal(t, k8sClusterConfigEntity.Active, foundConfig.Active)
	assert.Equal(t, k8sClusterConfigEntity.Description, foundConfig.Description)
}

func (suite *K8sClusterConfigProviderTestSuite) TestFindConfigByName() {
	t := suite.T()
	clusterConfig, err := suite.clusterConfigProvider.CreateConfig(k8sClusterConfigEntity)
	assert.NoError(t, err)
	assert.NotNil(t, clusterConfig.ID)

	foundConfig, err := suite.clusterConfigProvider.FindConfigByName(clusterConfig.ClusterName)
	assert.NoError(t, err)
	assert.Equal(t, k8sClusterConfigEntity.ClusterName, foundConfig.ClusterName)
	assert.Equal(t, k8sClusterConfigEntity.APIServerURL, foundConfig.APIServerURL)
	assert.Equal(t, k8sClusterConfigEntity.CACert, foundConfig.CACert)
	assert.Equal(t, k8sClusterConfigEntity.ClientCert, foundConfig.ClientCert)
	assert.Equal(t, k8sClusterConfigEntity.ClientKey, foundConfig.ClientKey)
	assert.Equal(t, k8sClusterConfigEntity.Token, foundConfig.Token)
	assert.Equal(t, k8sClusterConfigEntity.Username, foundConfig.Username)
	assert.Equal(t, k8sClusterConfigEntity.Password, foundConfig.Password)
	assert.Equal(t, k8sClusterConfigEntity.Active, foundConfig.Active)
	assert.Equal(t, k8sClusterConfigEntity.Description, foundConfig.Description)
}

func (suite *K8sClusterConfigProviderTestSuite) TestUpdateConfig() {
	t := suite.T()
	clusterConfig, err := suite.clusterConfigProvider.CreateConfig(k8sClusterConfigEntity)
	assert.NoError(t, err)
	assert.NotNil(t, clusterConfig.ID)

	clusterConfig.Token = "test"
	rows, err := suite.clusterConfigProvider.UpdateConfig(clusterConfig)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *K8sClusterConfigProviderTestSuite) TestGetRegionsByVisibility() {
	t := suite.T()
	entity, err := suite.clusterConfigProvider.GetRegionsByVisibility(true)
	assert.NoError(t, err)
	assert.NotNil(t, entity)
}
