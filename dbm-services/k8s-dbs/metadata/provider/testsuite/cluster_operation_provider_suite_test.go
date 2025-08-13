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
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var ClusterOperationEntity = &metaentity.ClusterOperationEntity{
	AddonType:    "addon_type_01",
	AddonVersion: "addon_version_01",
	OperationID:  1,
	Active:       true,
	Description:  "description_01",
}

var ClusterOperationEntityList = []*metaentity.ClusterOperationEntity{
	{
		AddonType:    "addon_type_01",
		AddonVersion: "addon_version_01",
		OperationID:  1,
		Active:       true,
		Description:  "description_01",
	},
	{
		AddonType:    "addon_type_02",
		AddonVersion: "addon_version_02",
		OperationID:  2,
		Active:       true,
		Description:  "description_02",
	},
}

type ClusterOperationProviderTestSuite struct {
	suite.Suite
	mySqlContainer              *testhelper.MySQLContainerWrapper
	clusterOperationProvider    provider.ClusterOperationProvider
	operationDefinitionProvider provider.OperationDefinitionProvider
	ctx                         context.Context
}

func (suite *ClusterOperationProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewClusterOperationDbAccess(db)
	definitionDbAccess := dbaccess.NewOperationDefinitionDbAccess(db)
	suite.clusterOperationProvider = provider.NewClusterOperationProvider(dbAccess, definitionDbAccess)
	suite.operationDefinitionProvider = provider.NewOperationDefinitionProvider(definitionDbAccess)

}

func (suite *ClusterOperationProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterOperationProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbClusterOperation, &model.ClusterOperationModel{})
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbOperationDefinition, &model.OperationDefinitionModel{})
}

func TestClusterOperationProvider(t *testing.T) {
	suite.Run(t, new(ClusterOperationProviderTestSuite))
}

func (suite *ClusterOperationProviderTestSuite) TestCreateClusterOperation() {
	t := suite.T()
	addedEntity, err := suite.clusterOperationProvider.CreateClusterOperation(ClusterOperationEntity)
	assert.NoError(t, err)
	assert.NotNil(t, addedEntity)
	assert.Equal(t, ClusterOperationEntity.AddonType, addedEntity.AddonType)
	assert.Equal(t, ClusterOperationEntity.AddonVersion, addedEntity.AddonVersion)
	assert.Equal(t, ClusterOperationEntity.OperationID, addedEntity.OperationID)
	assert.Equal(t, ClusterOperationEntity.Active, addedEntity.Active)
	assert.Equal(t, ClusterOperationEntity.Description, addedEntity.Description)
}

func (suite *ClusterOperationProviderTestSuite) TestListClusterOperations() {
	t := suite.T()

	for _, operationEntity := range ClusterOperationEntityList {
		result, err := suite.clusterOperationProvider.CreateClusterOperation(operationEntity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	for _, definitionEntity := range OperationDefinitionEntityList {
		result, err := suite.operationDefinitionProvider.CreateOperationDefinition(definitionEntity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}
	clusterOperations, err := suite.clusterOperationProvider.ListClusterOperations(pagination)
	assert.NoError(t, err)

	clusters := make(map[string]bool)
	for _, operation := range clusterOperations {
		clusters[operation.AddonType] = true
	}

	for _, operation := range ClusterOperationEntityList {
		assert.True(t, clusters[operation.AddonType], operation.AddonType)
	}

}
