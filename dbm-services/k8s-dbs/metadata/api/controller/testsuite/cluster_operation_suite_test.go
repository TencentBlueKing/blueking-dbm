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
	"bytes"
	"context"
	"encoding/json"
	"k8s-dbs/metadata/api/controller"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	vo "k8s-dbs/metadata/vo/request"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var clusterOperationRequest = vo.ClusterOperationRequest{
	AddonType:    "mysql",
	AddonVersion: "8.0",
	OperationID:  1,
	Description:  "创建测试集群",
	BKAuth:       baseBKAuth,
}

type ClusterOperationControllerTestSuite struct {
	suite.Suite
	mySQLContainer             *testhelper.MySQLContainerWrapper
	clusterOperationController *controller.ClusterOperationController
	ctx                        context.Context
	router                     *gin.Engine
}

func (suite *ClusterOperationControllerTestSuite) SetupSuite() {
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
	clusterOpDbAccess := dbaccess.NewClusterOperationDbAccess(db)
	opDefDbAccess := dbaccess.NewOperationDefinitionDbAccess(db)
	clusterOperationProvider := provider.NewClusterOperationProvider(clusterOpDbAccess, opDefDbAccess)
	clusterOperationController := controller.NewClusterOperationController(clusterOperationProvider)
	suite.clusterOperationController = clusterOperationController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/cluster_operation")
	{
		routerGroup.POST("", suite.clusterOperationController.CreateClusterOperation)
		routerGroup.GET("", suite.clusterOperationController.ListClusterOperations)
	}
	suite.router = r
}

func (suite *ClusterOperationControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterOperationControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbClusterOperation, &model.ClusterOperationModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbOperationDefinition, &model.OperationDefinitionModel{})
}

func TestClusterOperationController(t *testing.T) {
	suite.Run(t, new(ClusterOperationControllerTestSuite))
}

func (suite *ClusterOperationControllerTestSuite) TestCreateClusterOperation() {
	t := suite.T()
	jsonData, _ := json.Marshal(clusterOperationRequest)
	request, _ := http.NewRequest("POST", "/metadata/cluster_operation", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"active": true,
		"addonType": "mysql",
		"addonVersion": "8.0",
		"createdBy": "",
		"description": "创建测试集群",
		"id": 1,
		"operation": {
		  "active": false,
		  "createdBy": "",
		  "description": "",
		  "id": 0,
		  "operationName": "",
		  "operationTarget": "",
		  "updatedBy": ""
		},
		"operationId": 1,
		"updatedBy": ""
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *ClusterOperationControllerTestSuite) TestListClusterOperations() {
	t := suite.T()
	createMoreClusterOperation(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/cluster_operation?size=10", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": [
		{
		  "active": true,
		  "addonType": "mysql",
		  "addonVersion": "8.0",
		  "createdBy": "admin",
		  "description": "创建测试集群",
		  "id": 1,
		  "operation": {
			"active": true,
			"createdBy": "admin",
			"description": "测试操作定义",
			"id": 1,
			"operationName": "test-operation",
			"operationTarget": "cluster",
			"updatedBy": "admin"
		  },
		  "operationId": 1,
		  "updatedBy": "admin"
		},
		{
		  "active": true,
		  "addonType": "mysql",
		  "addonVersion": "8.0",
		  "createdBy": "admin",
		  "description": "创建测试集群",
		  "id": 2,
		  "operation": {
			"active": true,
			"createdBy": "admin",
			"description": "测试操作定义",
			"id": 2,
			"operationName": "test-operation",
			"operationTarget": "cluster",
			"updatedBy": "admin"
		  },
		  "operationId": 2,
		  "updatedBy": "admin"
		}
	  ],
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
