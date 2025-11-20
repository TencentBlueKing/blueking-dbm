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

var OperationDefinitionEntity = &metaentity.OperationDefinitionEntity{
	OperationName:   "operation_name_01",
	OperationTarget: "operation_target_01",
	Active:          true,
	Description:     "description_01",
}

var OperationDefinitionEntityList = []*metaentity.OperationDefinitionEntity{
	{
		OperationName:   "operation_name_01",
		OperationTarget: "operation_target_01",
		Active:          true,
		Description:     "description_01",
	},
	{
		OperationName:   "operation_name_02",
		OperationTarget: "operation_target_02",
		Active:          true,
		Description:     "description_02",
	},
}

type OperationDefinitionProviderTestSuite struct {
	suite.Suite
	mySqlContainer              *testhelper.MySQLContainerWrapper
	operationDefinitionProvider provider.OperationDefinitionProvider
	ctx                         context.Context
}

func (suite *OperationDefinitionProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewOperationDefinitionDbAccess(db)
	suite.operationDefinitionProvider = provider.NewOperationDefinitionProvider(dbAccess)
}

func (suite *OperationDefinitionProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *OperationDefinitionProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbOperationDefinition, &model.OperationDefinitionModel{})
}

func TestOperationDefinitionProvider(t *testing.T) {
	suite.Run(t, new(OperationDefinitionProviderTestSuite))
}

func (suite *OperationDefinitionProviderTestSuite) TestCreateOperationDefinition() {
	t := suite.T()
	createdEntity, err := suite.operationDefinitionProvider.CreateOperationDefinition(OperationDefinitionEntity)
	assert.NoError(t, err)
	assert.Equal(t, OperationDefinitionEntity.OperationName, createdEntity.OperationName)
	assert.Equal(t, OperationDefinitionEntity.OperationTarget, createdEntity.OperationTarget)
	assert.Equal(t, OperationDefinitionEntity.Active, createdEntity.Active)
	assert.Equal(t, OperationDefinitionEntity.Description, createdEntity.Description)
}

func (suite *OperationDefinitionProviderTestSuite) TestListOperationDefinitions() {
	t := suite.T()

	for _, entity := range OperationDefinitionEntityList {
		result, err := suite.operationDefinitionProvider.CreateOperationDefinition(entity)
		assert.NoError(t, err)
		assert.NotZero(t, result.ID)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}
	definitions, err := suite.operationDefinitionProvider.ListOperationDefinitions(pagination)
	assert.NoError(t, err)

	clusters := make(map[string]bool)
	for _, operation := range definitions {
		clusters[operation.OperationName] = true
	}

	for _, operation := range OperationDefinitionEntityList {
		assert.True(t, clusters[operation.OperationName], operation.OperationName)
	}
}
