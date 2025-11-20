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

var clusterRequestEntity = &metaenitty.ClusterRequestRecordEntity{
	RequestID:      "request_id_01",
	K8sClusterName: "k8s_cluster_name_01",
	ClusterName:    "cluster_name_01",
	NameSpace:      "namespace_01",
	RequestType:    "request_type_01",
	RequestParams:  "request_params_01",
	Status:         "status_01",
	Description:    "description_01",
}

var clusterRequestEntityList = []metaenitty.ClusterRequestRecordEntity{
	{
		RequestID:      "request_id_01",
		K8sClusterName: "k8s_cluster_name_01",
		ClusterName:    "cluster_name_01",
		NameSpace:      "namespace_01",
		RequestType:    "request_type_01",
		RequestParams:  "request_params_01",
		Status:         "status_01",
		Description:    "description_01",
	},
	{
		RequestID:      "request_id_02",
		K8sClusterName: "k8s_cluster_name_02",
		ClusterName:    "cluster_name_02",
		NameSpace:      "namespace_02",
		RequestType:    "request_type_02",
		RequestParams:  "request_params_02",
		Status:         "status_02",
		Description:    "description_02",
	},
}

type ClusterRequestProviderTestSuite struct {
	suite.Suite
	mySqlContainer  *testhelper.MySQLContainerWrapper
	clusterProvider provider.ClusterRequestRecordProvider
	ctx             context.Context
}

func (suite *ClusterRequestProviderTestSuite) SetupSuite() {
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
	clusterProvider := provider.NewClusterRequestRecordProvider(dbAccess)
	suite.clusterProvider = clusterProvider
}

func (suite *ClusterRequestProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterRequestProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbClusterRequestRecord, &model.ClusterRequestRecordModel{})
}

func TestClusterRequestProvider(t *testing.T) {
	suite.Run(t, new(ClusterRequestProviderTestSuite))
}

func (suite *ClusterRequestProviderTestSuite) TestCreateRequestRecord() {
	t := suite.T()
	request, err := suite.clusterProvider.CreateRequestRecord(clusterRequestEntity)
	assert.NoError(t, err)
	assert.Equal(t, clusterRequestEntity.RequestID, request.RequestID)
	assert.Equal(t, clusterRequestEntity.K8sClusterName, request.K8sClusterName)
	assert.Equal(t, clusterRequestEntity.ClusterName, request.ClusterName)
	assert.Equal(t, clusterRequestEntity.NameSpace, request.NameSpace)
	assert.Equal(t, clusterRequestEntity.RequestType, request.RequestType)
	assert.Equal(t, clusterRequestEntity.RequestParams, request.RequestParams)
	assert.Equal(t, clusterRequestEntity.Status, request.Status)
	assert.Equal(t, clusterRequestEntity.Description, request.Description)
}

func (suite *ClusterRequestProviderTestSuite) TestDeleteRequestRecordByID() {
	t := suite.T()
	request, err := suite.clusterProvider.CreateRequestRecord(clusterRequestEntity)
	assert.NoError(t, err)
	assert.NotNil(t, request.ID)

	rows, err := suite.clusterProvider.DeleteRequestRecordByID(request.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterRequestProviderTestSuite) TestFindRequestRecordByID() {
	t := suite.T()
	request, err := suite.clusterProvider.CreateRequestRecord(clusterRequestEntity)
	assert.NoError(t, err)
	assert.NotNil(t, request.ID)

	foundRequest, err := suite.clusterProvider.FindRequestRecordByID(request.ID)
	assert.NoError(t, err)
	assert.Equal(t, request.RequestID, foundRequest.RequestID)
	assert.Equal(t, request.K8sClusterName, foundRequest.K8sClusterName)
	assert.Equal(t, request.ClusterName, foundRequest.ClusterName)
	assert.Equal(t, request.NameSpace, foundRequest.NameSpace)
	assert.Equal(t, request.RequestType, foundRequest.RequestType)
	assert.Equal(t, request.RequestParams, foundRequest.RequestParams)
	assert.Equal(t, request.Status, foundRequest.Status)
	assert.Equal(t, request.Description, foundRequest.Description)
}

func (suite *ClusterRequestProviderTestSuite) TestUpdateRequestRecord() {
	t := suite.T()
	request, err := suite.clusterProvider.CreateRequestRecord(clusterRequestEntity)
	assert.NoError(t, err)
	assert.NotNil(t, request.ID)

	request.Status = "updated_status"
	rows, err := suite.clusterProvider.UpdateRequestRecord(request)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterRequestProviderTestSuite) TestListRecords() {
	t := suite.T()
	for _, entity := range clusterRequestEntityList {
		_, err := suite.clusterProvider.CreateRequestRecord(&entity)
		assert.NoError(t, err)
	}

	pagin := commentity.Pagination{
		Page:  0,
		Limit: 10,
	}

	params := &metaenitty.ClusterRequestQueryParams{
		RequestID: "request_id_01",
	}

	records, _, err := suite.clusterProvider.ListRecords(params, &pagin)
	assert.NoError(t, err)

	recordNames := make(map[string]bool)
	for _, record := range records {
		recordNames[record.RequestID] = true
	}

	for _, record := range clusterRequestEntityList {
		assert.True(t, recordNames[record.RequestID], record.RequestID)
	}

}
