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
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	models "k8s-dbs/metadata/model"
)

var clusterRequestSample = &models.ClusterRequestRecordModel{
	RequestID:   "req-12345",
	RequestType: "CreateCluster",
}

var batchClusterRequestSamples = []*models.ClusterRequestRecordModel{
	{
		RequestID:   "req-11111",
		RequestType: "CreateCluster",
	},
	{
		RequestID:   "req-22222",
		RequestType: "ScaleCluster",
	},
	{
		RequestID:   "req-33333",
		RequestType: "DeleteCluster",
	},
}

type ClusterRequestDbAccessTestSuite struct {
	suite.Suite
	ctx            context.Context
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.ClusterRequestRecordDbAccess
}

func (suite *ClusterRequestDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewClusterRequestRecordDbAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *ClusterRequestDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterRequestDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbClusterRequestRecord, &models.ClusterRequestRecordModel{})
}

func (suite *ClusterRequestDbAccessTestSuite) TestCreateClusterRequest() {
	t := suite.T()
	clusterRequest, err := suite.dbAccess.Create(clusterRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterRequest.ID)
	assert.Equal(t, clusterRequestSample.RequestID, clusterRequest.RequestID)
	assert.Equal(t, clusterRequestSample.RequestType, clusterRequest.RequestType)
}

func (suite *ClusterRequestDbAccessTestSuite) TestGetClusterRequest() {
	t := suite.T()
	clusterRequest, err := suite.dbAccess.Create(clusterRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterRequest.ID)

	foundClusterRequest, err := suite.dbAccess.FindByID(clusterRequest.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundClusterRequest)
	assert.Equal(t, clusterRequest.ID, foundClusterRequest.ID)
	assert.Equal(t, clusterRequest.RequestID, foundClusterRequest.RequestID)
	assert.Equal(t, clusterRequest.RequestType, foundClusterRequest.RequestType)
}

func (suite *ClusterRequestDbAccessTestSuite) TestUpdateClusterRequest() {
	t := suite.T()
	clusterRequest, err := suite.dbAccess.Create(clusterRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterRequest.ID)

	newClusterRequest := &models.ClusterRequestRecordModel{
		ID:          clusterRequest.ID,
		RequestID:   "req-updated",
		RequestType: "UpdateCluster",
	}
	rows, err := suite.dbAccess.Update(newClusterRequest)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterRequestDbAccessTestSuite) TestDeleteClusterRequest() {
	t := suite.T()
	clusterRequest, err := suite.dbAccess.Create(clusterRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterRequest.ID)

	rows, err := suite.dbAccess.DeleteByID(clusterRequest.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterRequestDbAccessTestSuite) TestListClusterRequestByPage() {
	t := suite.T()
	for _, clusterRequest := range batchClusterRequestSamples {
		_, err := suite.dbAccess.Create(clusterRequest)
		assert.NoError(t, err)
	}

	params := &entitys.ClusterRequestQueryParams{}
	pagination := &entity.Pagination{
		Page:  0,
		Limit: 10,
	}

	clusterRequests, total, err := suite.dbAccess.ListByPage(params, pagination)
	assert.NoError(t, err)
	assert.Equal(t, len(batchClusterRequestSamples), len(clusterRequests))
	assert.Equal(t, uint64(len(batchClusterRequestSamples)), total)

	requestMap := make(map[string]models.ClusterRequestRecordModel)
	for _, request := range clusterRequests {
		requestMap[request.RequestID] = *request
	}

	for _, sample := range batchClusterRequestSamples {
		foundRequest, ok := requestMap[sample.RequestID]
		assert.True(t, ok, "Request with ID %s not found", sample.RequestID)
		assert.Equal(t, sample.RequestID, foundRequest.RequestID)
		assert.Equal(t, sample.RequestType, foundRequest.RequestType)
	}
}

func TestClusterRequestDbAccess(t *testing.T) {
	suite.Run(t, new(ClusterRequestDbAccessTestSuite))
}
