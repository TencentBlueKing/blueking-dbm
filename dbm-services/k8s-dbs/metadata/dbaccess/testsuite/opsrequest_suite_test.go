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
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var opsRequestSample = &model.K8sCrdOpsRequestModel{
	CrdClusterID:       1,
	K8sClusterConfigID: 1,
	RequestID:          "req-12345",
	OpsRequestName:     "scale-cluster",
	OpsRequestType:     "scale",
}

type OpsRequestDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sCrdOpsRequestDbAccess
	ctx            context.Context
}

func (suite *OpsRequestDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbAccess
}

func (suite *OpsRequestDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *OpsRequestDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdOpsRequest, &model.K8sCrdOpsRequestModel{})
}

func (suite *OpsRequestDbAccessTestSuite) TestCreateOpsRequest() {
	t := suite.T()
	opsRequest, err := suite.dbAccess.Create(opsRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, opsRequest.ID)
	assert.Equal(t, opsRequestSample.CrdClusterID, opsRequest.CrdClusterID)
	assert.Equal(t, opsRequestSample.K8sClusterConfigID, opsRequest.K8sClusterConfigID)
	assert.Equal(t, opsRequestSample.RequestID, opsRequest.RequestID)
	assert.Equal(t, opsRequestSample.OpsRequestName, opsRequest.OpsRequestName)
	assert.Equal(t, opsRequestSample.OpsRequestType, opsRequest.OpsRequestType)
}

func (suite *OpsRequestDbAccessTestSuite) TestDeleteOpsRequest() {
	t := suite.T()
	opsRequest, err := suite.dbAccess.Create(opsRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, opsRequest.ID)

	rows, err := suite.dbAccess.DeleteByID(opsRequest.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *OpsRequestDbAccessTestSuite) TestUpdateOpsRequest() {
	t := suite.T()
	opsRequest, err := suite.dbAccess.Create(opsRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, opsRequest.ID)

	newOpsRequest := &model.K8sCrdOpsRequestModel{
		ID:                 opsRequest.ID,
		CrdClusterID:       2,
		K8sClusterConfigID: 2,
		RequestID:          "req-updated",
		OpsRequestName:     "updated-request",
		OpsRequestType:     "update",
	}
	rows, err := suite.dbAccess.Update(newOpsRequest)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *OpsRequestDbAccessTestSuite) TestGetOpsRequest() {
	t := suite.T()
	opsRequest, err := suite.dbAccess.Create(opsRequestSample)
	assert.NoError(t, err)
	assert.NotZero(t, opsRequest.ID)

	foundOpsRequest, err := suite.dbAccess.FindByID(opsRequest.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundOpsRequest)

	assert.Equal(t, opsRequest.CrdClusterID, foundOpsRequest.CrdClusterID)
	assert.Equal(t, opsRequest.K8sClusterConfigID, foundOpsRequest.K8sClusterConfigID)
	assert.Equal(t, opsRequest.RequestID, foundOpsRequest.RequestID)
	assert.Equal(t, opsRequest.OpsRequestName, foundOpsRequest.OpsRequestName)
	assert.Equal(t, opsRequest.OpsRequestType, foundOpsRequest.OpsRequestType)
}

func TestOpsRequestDbAccess(t *testing.T) {
	suite.Run(t, new(OpsRequestDbAccessTestSuite))
}
