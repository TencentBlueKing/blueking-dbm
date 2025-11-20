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

type ClusterRequestControllerTestSuite struct {
	suite.Suite
	mySQLContainer           *testhelper.MySQLContainerWrapper
	clusterRequestController *controller.ClusterRequestRecordController
	ctx                      context.Context
	router                   *gin.Engine
}

func (suite *ClusterRequestControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewClusterRequestRecordDbAccess(db)
	clusterRequestProvider := provider.NewClusterRequestRecordProvider(dbAccess)
	clusterRequestController := controller.NewClusterRequestRecordController(clusterRequestProvider)
	suite.clusterRequestController = clusterRequestController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/cluster_request_record")
	{
		routerGroup.GET("", suite.clusterRequestController.ListClusterRecords)
	}
	suite.router = r
}

func (suite *ClusterRequestControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterRequestControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbClusterRequestRecord, &model.ClusterRequestRecordModel{})
}

func TestClusterRequestController(t *testing.T) {
	suite.Run(t, new(ClusterRequestControllerTestSuite))
}

func (suite *ClusterRequestControllerTestSuite) TestListClusterRequests() {
	t := suite.T()
	createMoreClusterRequest(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/cluster_request_record?startTime=2024-01-01 00:00:00&endTime=2026-01-01 00:00:00&size=10", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"count": 2,
		"result": [
		  {
			"clusterName": "test-cluster",
			"createdBy": "admin",
			"description": "创建测试集群",
			"id": 1,
			"k8sClusterName": "default",
			"nameSpace": "default",
			"requestId": "req-123456",
			"requestParams": "{\"param1\":\"value1\",\"param2\":\"value2\"}",
			"requestType": "CREATE",
			"requestTypeAlias": "",
			"status": "SUCCESS",
			"updatedBy": "admin"
		  },
		  {
			"clusterName": "test-cluster",
			"createdBy": "admin",
			"description": "创建测试集群",
			"id": 2,
			"k8sClusterName": "default",
			"nameSpace": "default",
			"requestId": "req-123456",
			"requestParams": "{\"param1\":\"value1\",\"param2\":\"value2\"}",
			"requestType": "CREATE",
			"requestTypeAlias": "",
			"status": "SUCCESS",
			"updatedBy": "admin"
		  }
		]
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
