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
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sCrdOpsRequestEntity = &metaenitty.K8sCrdOpsRequestEntity{
	CrdClusterID:       uint64(1),
	K8sClusterConfigID: uint64(1),
	RequestID:          "request_id_01",
	OpsRequestName:     "ops_request_name_01",
	OpsRequestType:     "ops_request_type_01",
	Metadata:           "metadata_01",
	Spec:               "spec_01",
	Status:             "status_01",
	Description:        "description_01",
}

var k8sCrdOpsRequestEntityList = []metaenitty.K8sCrdOpsRequestEntity{
	{
		CrdClusterID:       uint64(1),
		K8sClusterConfigID: uint64(1),
		RequestID:          "request_id_01",
		OpsRequestName:     "ops_request_name_01",
		OpsRequestType:     "ops_request_type_01",
		Metadata:           "metadata_01",
		Spec:               "spec_01",
		Status:             "status_01",
		Description:        "description_01",
	},
	{
		CrdClusterID:       uint64(2),
		K8sClusterConfigID: uint64(2),
		RequestID:          "request_id_02",
		OpsRequestName:     "ops_request_name_02",
		OpsRequestType:     "ops_request_type_02",
		Metadata:           "metadata_02",
		Spec:               "spec_02",
		Status:             "status_02",
		Description:        "description_02",
	},
}

type OpsrequestProviderTestSuite struct {
	suite.Suite
	mySqlContainer  *testhelper.MySQLContainerWrapper
	clusterProvider provider.K8sCrdOpsRequestProvider
	ctx             context.Context
}

func (suite *OpsrequestProviderTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)
	clusterProvider := provider.NewK8sCrdOpsRequestProvider(dbAccess)
	suite.clusterProvider = clusterProvider
}

func (suite *OpsrequestProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *OpsrequestProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdOpsRequest, &model.K8sCrdOpsRequestModel{})
}

func TestOpsrequestProvider(t *testing.T) {
	suite.Run(t, new(OpsrequestProviderTestSuite))
}

func (suite *OpsrequestProviderTestSuite) TestCreateOpsRequest() {
	t := suite.T()
	entity, err := suite.clusterProvider.CreateOpsRequest(k8sCrdOpsRequestEntity)
	assert.NoError(t, err)
	assert.Equal(t, k8sCrdOpsRequestEntity.CrdClusterID, entity.CrdClusterID)
	assert.Equal(t, k8sCrdOpsRequestEntity.K8sClusterConfigID, entity.K8sClusterConfigID)
	assert.Equal(t, k8sCrdOpsRequestEntity.RequestID, entity.RequestID)
	assert.Equal(t, k8sCrdOpsRequestEntity.OpsRequestName, entity.OpsRequestName)
	assert.Equal(t, k8sCrdOpsRequestEntity.OpsRequestType, entity.OpsRequestType)
	assert.Equal(t, k8sCrdOpsRequestEntity.Metadata, entity.Metadata)
	assert.Equal(t, k8sCrdOpsRequestEntity.Spec, entity.Spec)
	assert.Equal(t, k8sCrdOpsRequestEntity.Status, entity.Status)
	assert.Equal(t, k8sCrdOpsRequestEntity.Description, entity.Description)

}

func (suite *OpsrequestProviderTestSuite) TestDeleteOpsRequestByID() {
	t := suite.T()
	entity, err := suite.clusterProvider.CreateOpsRequest(k8sCrdOpsRequestEntity)
	assert.NoError(t, err)

	rows, err := suite.clusterProvider.DeleteOpsRequestByID(entity.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *OpsrequestProviderTestSuite) TestFindOpsRequestByID() {
	t := suite.T()
	entity, err := suite.clusterProvider.CreateOpsRequest(k8sCrdOpsRequestEntity)
	assert.NoError(t, err)
	assert.NotZero(t, entity.ID)

	foundEntity, err := suite.clusterProvider.FindOpsRequestByID(entity.ID)
	assert.NoError(t, err)
	assert.Equal(t, entity.CrdClusterID, foundEntity.CrdClusterID)
	assert.Equal(t, entity.K8sClusterConfigID, foundEntity.K8sClusterConfigID)
	assert.Equal(t, entity.RequestID, foundEntity.RequestID)
	assert.Equal(t, entity.OpsRequestName, foundEntity.OpsRequestName)
	assert.Equal(t, entity.OpsRequestType, foundEntity.OpsRequestType)
	assert.Equal(t, entity.Metadata, foundEntity.Metadata)
	assert.Equal(t, entity.Spec, foundEntity.Spec)
	assert.Equal(t, entity.Status, foundEntity.Status)
	assert.Equal(t, entity.Description, foundEntity.Description)
}

func (suite *OpsrequestProviderTestSuite) TestUpdateOpsRequest() {
	t := suite.T()
	entity, err := suite.clusterProvider.CreateOpsRequest(k8sCrdOpsRequestEntity)
	assert.NoError(t, err)
	assert.NotZero(t, entity.ID)

	entity.OpsRequestName = "updated_ops_request_name"
	entity.Status = "updated_status"

	rows, err := suite.clusterProvider.UpdateOpsRequest(entity)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}
