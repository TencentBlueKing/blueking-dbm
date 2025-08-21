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

var componentOperationRequest = vo.ComponentOperationRequest{
	AddonType:        "mysql",
	AddonVersion:     "8.0",
	ComponentName:    "mysql-server",
	ComponentVersion: "8.0",
	OperationID:      1,
	Description:      "创建测试组件",
	BKAuth:           baseBKAuth,
}

type ComponentOperationControllerTestSuite struct {
	suite.Suite
	mySQLContainer               *testhelper.MySQLContainerWrapper
	componentOperationController *controller.ComponentOperationController
	ctx                          context.Context
	router                       *gin.Engine
}

func (suite *ComponentOperationControllerTestSuite) SetupSuite() {
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
	componentOpDbAccess := dbaccess.NewComponentOperationDbAccess(db)
	opDefDbAccess := dbaccess.NewOperationDefinitionDbAccess(db)
	componentOpProvider := provider.NewComponentOperationProvider(componentOpDbAccess, opDefDbAccess)
	componentOperationController := controller.NewComponentOperationController(componentOpProvider)
	suite.componentOperationController = componentOperationController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/component_operation")
	{
		routerGroup.POST("", suite.componentOperationController.CreateComponentOperation)
		routerGroup.GET("", suite.componentOperationController.ListComponentOperations)
	}
	suite.router = r
}

func (suite *ComponentOperationControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentOperationControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbComponentOperation, &model.ComponentOperationModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbOperationDefinition, &model.OperationDefinitionModel{})
}

func TestComponentOperationController(t *testing.T) {
	suite.Run(t, new(ComponentOperationControllerTestSuite))
}

func (suite *ComponentOperationControllerTestSuite) TestCreateComponentOperation() {
	t := suite.T()
	jsonData, _ := json.Marshal(componentOperationRequest)
	request, _ := http.NewRequest("POST", "/metadata/component_operation", bytes.NewReader(jsonData))
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
		"componentName": "mysql-server",
		"componentVersion": "8.0",
		"createdBy": "",
		"description": "创建测试组件",
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

func (suite *ComponentOperationControllerTestSuite) TestListComponentOperations() {
	t := suite.T()
	createMoreComponentOperation(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/component_operation?size=10", nil)
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
		  "componentName": "mysql-server",
		  "componentVersion": "8.0",
		  "createdBy": "admin",
		  "description": "创建测试组件",
		  "id": 1,
		  "operation": {
			"active": true,
			"createdBy": "admin",
			"description": "测试组件操作定义",
			"id": 1,
			"operationName": "test-component-operation",
			"operationTarget": "component",
			"updatedBy": "admin"
		  },
		  "operationId": 1,
		  "updatedBy": "admin"
		},
		{
		  "active": true,
		  "addonType": "mysql",
		  "addonVersion": "8.0",
		  "componentName": "mysql-server",
		  "componentVersion": "8.0",
		  "createdBy": "admin",
		  "description": "创建测试组件",
		  "id": 2,
		  "operation": {
			"active": true,
			"createdBy": "admin",
			"description": "测试组件操作定义",
			"id": 2,
			"operationName": "test-component-operation",
			"operationTarget": "component",
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
