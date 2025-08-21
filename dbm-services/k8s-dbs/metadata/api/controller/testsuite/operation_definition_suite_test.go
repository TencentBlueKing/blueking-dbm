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

var operationDefinitionRequest = vo.OperationDefinitionRequest{
	OperationName:   "test-operation",
	OperationTarget: "cluster",
	Description:     "测试操作定义",
	BKAuth:          baseBKAuth,
}

type OperationDefinitionControllerTestSuite struct {
	suite.Suite
	mySQLContainer                *testhelper.MySQLContainerWrapper
	operationDefinitionController *controller.OperationDefinitionController
	ctx                           context.Context
	router                        *gin.Engine
}

func (suite *OperationDefinitionControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewOperationDefinitionDbAccess(db)
	operationDefinitionProvider := provider.NewOperationDefinitionProvider(dbAccess)
	operationDefinitionController := controller.NewOperationDefinitionController(operationDefinitionProvider)
	suite.operationDefinitionController = operationDefinitionController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/operation_definition")
	{
		routerGroup.POST("", suite.operationDefinitionController.CreateOperationDefinition)
		routerGroup.GET("", suite.operationDefinitionController.ListOperationDefinitions)
	}
	suite.router = r
}

func (suite *OperationDefinitionControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *OperationDefinitionControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbOperationDefinition, &model.OperationDefinitionModel{})
}

func TestOperationDefinitionController(t *testing.T) {
	suite.Run(t, new(OperationDefinitionControllerTestSuite))
}

func (suite *OperationDefinitionControllerTestSuite) TestCreateOperationDefinition() {
	t := suite.T()
	jsonData, _ := json.Marshal(operationDefinitionRequest)
	request, _ := http.NewRequest("POST", "/metadata/operation_definition", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"active": true,
		"createdBy": "",
		"description": "测试操作定义",
		"id": 1,
		"operationName": "test-operation",
		"operationTarget": "cluster",
		"updatedBy": ""
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *OperationDefinitionControllerTestSuite) TestListOperationDefinitions() {
	t := suite.T()
	createMoreOperationDefinition(suite.mySQLContainer, 2)

	request, _ := http.NewRequest("GET", "/metadata/operation_definition?size=10", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": [
		{
		  "active": true,
		  "createdBy": "admin",
		  "description": "测试操作定义",
		  "id": 1,
		  "operationName": "test-operation",
		  "operationTarget": "cluster",
		  "updatedBy": "admin"
		},
		{
		  "active": true,
		  "createdBy": "admin",
		  "description": "测试操作定义",
		  "id": 2,
		  "operationName": "test-operation",
		  "operationTarget": "cluster",
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
