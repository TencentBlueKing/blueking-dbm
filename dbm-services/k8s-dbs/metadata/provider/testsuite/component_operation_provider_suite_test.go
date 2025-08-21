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

var componentOperationEntity = &metaenitty.ComponentOperationEntity{
	AddonType:        "addon_type_01",
	AddonVersion:     "addon_version_01",
	ComponentName:    "component_name_01",
	ComponentVersion: "component_version_01",
	OperationID:      uint64(1),
	Active:           true,
	Description:      "description_01",
}

var componentOperationEntityList = []metaenitty.ComponentOperationEntity{
	{
		AddonType:        "addon_type_01",
		AddonVersion:     "addon_version_01",
		ComponentName:    "component_name_01",
		ComponentVersion: "component_version_01",
		OperationID:      uint64(1),
		Active:           true,
		Description:      "description_01",
	},
	{
		AddonType:        "addon_type_02",
		AddonVersion:     "addon_version_02",
		ComponentName:    "component_name_02",
		ComponentVersion: "component_version_02",
		OperationID:      uint64(2),
		Active:           true,
		Description:      "description_02",
	},
}

type ComponentOperationProviderTestSuite struct {
	suite.Suite
	mySqlContainer     *testhelper.MySQLContainerWrapper
	clusterProvider    provider.ComponentOperationProvider
	definitionProvider provider.OperationDefinitionProvider
	ctx                context.Context
}

func (suite *ComponentOperationProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewComponentOperationDbAccess(db)
	opDefDBAccess := dbaccess.NewOperationDefinitionDbAccess(db)
	clusterProvider := provider.NewComponentOperationProvider(dbAccess, opDefDBAccess)
	definitionProvider := provider.NewOperationDefinitionProvider(opDefDBAccess)
	suite.clusterProvider = clusterProvider
	suite.definitionProvider = definitionProvider
}

func (suite *ComponentOperationProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentOperationProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbComponentOperation, &model.ComponentOperationModel{})
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbOperationDefinition, &model.OperationDefinitionModel{})
}

func TestComponentOperationProvider(t *testing.T) {
	suite.Run(t, new(ComponentOperationProviderTestSuite))
}

func (suite *ComponentOperationProviderTestSuite) TestCreateComponentOperation() {
	t := suite.T()
	addedEntity, err := suite.clusterProvider.CreateComponentOperation(componentOperationEntity)
	assert.NoError(t, err)
	assert.Equal(t, componentOperationEntity.AddonType, addedEntity.AddonType)
	assert.Equal(t, componentOperationEntity.AddonVersion, addedEntity.AddonVersion)
	assert.Equal(t, componentOperationEntity.ComponentName, addedEntity.ComponentName)
	assert.Equal(t, componentOperationEntity.ComponentVersion, addedEntity.ComponentVersion)
	assert.Equal(t, componentOperationEntity.OperationID, addedEntity.OperationID)
	assert.Equal(t, componentOperationEntity.Active, addedEntity.Active)
	assert.Equal(t, componentOperationEntity.Description, addedEntity.Description)
}

func (suite *ComponentOperationProviderTestSuite) TestListComponentOperation() {
	t := suite.T()
	for _, entity := range componentOperationEntityList {
		result, err := suite.clusterProvider.CreateComponentOperation(&entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	for _, entity := range OperationDefinitionEntityList {
		result, err := suite.definitionProvider.CreateOperationDefinition(entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}

	operations, err := suite.clusterProvider.ListComponentOperations(pagin)
	assert.NoError(t, err)

	componentNames := make(map[string]bool)
	for _, component := range operations {
		componentNames[component.AddonType] = true
	}

	for _, component := range componentOperationEntityList {
		assert.True(t, componentNames[component.AddonType], component.AddonType)
	}
}
