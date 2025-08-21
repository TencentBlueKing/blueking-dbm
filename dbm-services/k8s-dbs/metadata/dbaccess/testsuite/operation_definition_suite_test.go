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
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var operationDefinitionSample = &model.OperationDefinitionModel{
	OperationName:   "create-cluster",
	OperationTarget: "cluster",
}

var batchOperationDefinitionSamples = []*model.OperationDefinitionModel{
	{
		OperationName:   "delete-cluster",
		OperationTarget: "cluster",
	},
	{
		OperationName:   "scale-component",
		OperationTarget: "component",
	},
}

type OperationDefinitionDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.OperationDefinitionDbAccess
	ctx            context.Context
}

func (suite *OperationDefinitionDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbAccess
}

func (suite *OperationDefinitionDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *OperationDefinitionDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbOperationDefinition, &model.OperationDefinitionModel{})
}

func (suite *OperationDefinitionDbAccessTestSuite) TestCreateOperationDefinition() {
	t := suite.T()
	operationDef, err := suite.dbAccess.Create(operationDefinitionSample)
	assert.NoError(t, err)
	assert.NotZero(t, operationDef.ID)
	assert.Equal(t, operationDefinitionSample.OperationName, operationDef.OperationName)
	assert.Equal(t, operationDefinitionSample.OperationTarget, operationDef.OperationTarget)
}

func (suite *OperationDefinitionDbAccessTestSuite) TestGetOperationDefinition() {
	t := suite.T()
	operationDef, err := suite.dbAccess.Create(operationDefinitionSample)
	assert.NoError(t, err)
	assert.NotZero(t, operationDef.ID)

	foundOperationDef, err := suite.dbAccess.FindByID(operationDef.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundOperationDef)

	assert.Equal(t, operationDef.OperationName, foundOperationDef.OperationName)
	assert.Equal(t, operationDef.OperationTarget, foundOperationDef.OperationTarget)
}

func (suite *OperationDefinitionDbAccessTestSuite) TestListOperationDefinitionsByPage() {
	t := suite.T()
	for _, sample := range batchOperationDefinitionSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}

	operationDefs, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(len(batchOperationDefinitionSamples)), total)
	assert.Equal(t, len(batchOperationDefinitionSamples), len(operationDefs))

	operationDefMap := make(map[string]model.OperationDefinitionModel)
	for _, def := range operationDefs {
		operationDefMap[def.OperationName] = def
	}

	for _, sample := range batchOperationDefinitionSamples {
		fetchedDef, ok := operationDefMap[sample.OperationName]
		assert.True(t, ok, "OperationDefinition with name %s not found", sample.OperationName)
		assert.Equal(t, sample.OperationTarget, fetchedDef.OperationTarget)
	}
}

func TestOperationDefinitionDbAccess(t *testing.T) {
	suite.Run(t, new(OperationDefinitionDbAccessTestSuite))
}
