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

var componentOperationSample = &model.ComponentOperationModel{
	AddonType:        "mysql",
	AddonVersion:     "8.0.30",
	ComponentName:    "mysql-server",
	ComponentVersion: "8.0.30",
	OperationID:      1,
}

var batchComponentOperationSamples = []*model.ComponentOperationModel{
	{
		AddonType:        "redis",
		AddonVersion:     "7.0.0",
		ComponentName:    "redis-server",
		ComponentVersion: "7.0.0",
		OperationID:      2,
	},
	{
		AddonType:        "mongodb",
		AddonVersion:     "6.0.0",
		ComponentName:    "mongodb-server",
		ComponentVersion: "6.0.0",
		OperationID:      3,
	},
}

type ComponentOperationDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.ComponentOperationDbAccess
	ctx            context.Context
}

func (suite *ComponentOperationDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbAccess
}

func (suite *ComponentOperationDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentOperationDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbComponentOperation, &model.ComponentOperationModel{})
}

func (suite *ComponentOperationDbAccessTestSuite) TestCreateComponentOperation() {
	t := suite.T()
	componentOp, err := suite.dbAccess.Create(componentOperationSample)
	assert.NoError(t, err)
	assert.NotZero(t, componentOp.ID)
	assert.Equal(t, componentOperationSample.AddonType, componentOp.AddonType)
	assert.Equal(t, componentOperationSample.AddonVersion, componentOp.AddonVersion)
	assert.Equal(t, componentOperationSample.ComponentName, componentOp.ComponentName)
	assert.Equal(t, componentOperationSample.ComponentVersion, componentOp.ComponentVersion)
	assert.Equal(t, componentOperationSample.OperationID, componentOp.OperationID)
}

func (suite *ComponentOperationDbAccessTestSuite) TestListComponentOperationsByPage() {
	t := suite.T()
	for _, sample := range batchComponentOperationSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}

	componentOps, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(len(batchComponentOperationSamples)), total)
	assert.Equal(t, len(batchComponentOperationSamples), len(componentOps))

	componentOpMap := make(map[string]model.ComponentOperationModel)
	for _, op := range componentOps {
		componentOpMap[op.ComponentName] = op
	}

	for _, sample := range batchComponentOperationSamples {
		fetchedOp, ok := componentOpMap[sample.ComponentName]
		assert.True(t, ok, "ComponentOperation with name %s not found", sample.ComponentName)
		assert.Equal(t, sample.AddonType, fetchedOp.AddonType)
		assert.Equal(t, sample.AddonVersion, fetchedOp.AddonVersion)
		assert.Equal(t, sample.ComponentVersion, fetchedOp.ComponentVersion)
		assert.Equal(t, sample.OperationID, fetchedOp.OperationID)
	}
}

func TestCmpOperationDbAccessTestSt(t *testing.T) {
	suite.Run(t, new(ComponentOperationDbAccessTestSuite))
}
