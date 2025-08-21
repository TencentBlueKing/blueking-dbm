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
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"

	"k8s-dbs/common/entity"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
)

var clusterOperationSample = &model.ClusterOperationModel{
	AddonType:    "mysql",
	AddonVersion: "8.0.30",
	OperationID:  1,
}

var batchClusterOperationSamples = []*model.ClusterOperationModel{
	{
		AddonType:    "mysql",
		AddonVersion: "8.0.30",
		OperationID:  1,
	},
	{
		AddonType:    "redis",
		AddonVersion: "7.0.0",
		OperationID:  2,
	},
}

type ClusterOperationDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.ClusterOperationDbAccess
	ctx            context.Context
}

func (suite *ClusterOperationDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbAccess
}

func (suite *ClusterOperationDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterOperationDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbClusterOperation, &model.ClusterOperationModel{})
}

func (suite *ClusterOperationDbAccessTestSuite) TestCreateClusterOperation() {
	t := suite.T()
	clusterOp, err := suite.dbAccess.Create(clusterOperationSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterOp.ID)
	assert.Equal(t, clusterOperationSample.AddonType, clusterOp.AddonType)
	assert.Equal(t, clusterOperationSample.AddonVersion, clusterOp.AddonVersion)
	assert.Equal(t, clusterOperationSample.OperationID, clusterOp.OperationID)
}

func (suite *ClusterOperationDbAccessTestSuite) TestListClusterOperationByPage() {
	t := suite.T()
	for _, sample := range batchClusterOperationSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	pagination := entity.Pagination{
		Page:  0,
		Limit: 10,
	}

	clusterOps, total, err := suite.dbAccess.ListByPage(pagination)
	assert.NoError(t, err)
	assert.Equal(t, int64(len(batchClusterOperationSamples)), total)
	assert.Equal(t, len(batchClusterOperationSamples), len(clusterOps))

	opMap := make(map[string]model.ClusterOperationModel)
	for _, clusterOp := range clusterOps {
		key := clusterOp.AddonType + "-" + clusterOp.AddonVersion
		opMap[key] = clusterOp
	}

	for _, sample := range batchClusterOperationSamples {
		key := sample.AddonType + "-" + sample.AddonVersion
		foundOp, ok := opMap[key]
		assert.True(t, ok, "ClusterOperation with key %s not found", key)
		assert.Equal(t, sample.AddonType, foundOp.AddonType)
		assert.Equal(t, sample.AddonVersion, foundOp.AddonVersion)
		assert.Equal(t, sample.OperationID, foundOp.OperationID)
	}
}

func TestClusterOperationDbAccess(t *testing.T) {
	suite.Run(t, new(ClusterOperationDbAccessTestSuite))
}
