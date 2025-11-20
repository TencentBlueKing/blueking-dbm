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
	"k8s-dbs/metadata/api/controller"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

type OpsRequestControllerTestSuite struct {
	suite.Suite
	mySQLContainer       *testhelper.MySQLContainerWrapper
	opsRequestController *controller.OpsController
	ctx                  context.Context
	router               *gin.Engine
}

func (suite *OpsRequestControllerTestSuite) SetupSuite() {
	suite.ctx = context.Background()
	mySQLContainer, err := testhelper.NewMySQLContainerWrapper(suite.ctx)
	if err != nil {
		log.Fatal(err)
	}
	suite.mySQLContainer = mySQLContainer
	db, err := testhelper.InitDBConnection(mySQLContainer.ConnStr)
	if err != nil {
		log.Fatal(err)
	}
	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)
	opsRequestProvider := provider.NewK8sCrdOpsRequestProvider(dbAccess)
	opsRequestController := controller.NewOpsController(opsRequestProvider)
	suite.opsRequestController = opsRequestController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/ops")
	{
		routerGroup.GET("/:id", suite.opsRequestController.GetOps)
	}
	suite.router = r
}

func (suite *OpsRequestControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *OpsRequestControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sCrdOpsRequest, &model.K8sCrdOpsRequestModel{})
}

func TestOpsRequestController(t *testing.T) {
	suite.Run(t, new(OpsRequestControllerTestSuite))
}

func (suite *OpsRequestControllerTestSuite) TestGetOpsRequest() {
	t := suite.T()
	createMoreOpsRequest(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/ops/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"crdClusterId": 1,
		"createdBy": "admin",
		"description": "Test opsrequest",
		"id": 1,
		"k8sClusterConfigId": 1,
		"metadata": "{\"labels\":{\"app\":\"test\"}}",
		"opsrequestName": "test-opsrequest",
		"opsrequestType": "backup",
		"requestId": "test-request-001",
		"spec": "{\"backup\":{\"schedule\":\"0 2 * * *\"}}",
		"status": "pending",
		"updatedBy": "admin"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
