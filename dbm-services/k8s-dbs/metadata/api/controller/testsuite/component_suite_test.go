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
	"k8s-dbs/common/types"
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
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var operationTime = "2025-01-01 12:00:00"

type ComponentControllerTestSuite struct {
	suite.Suite
	mySQLContainer      *testhelper.MySQLContainerWrapper
	componentController *controller.ComponentController
	ctx                 context.Context
	router              *gin.Engine
}

func (suite *ComponentControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	componentProvider := provider.NewK8sCrdComponentProvider(dbAccess)
	componentController := controller.NewComponentController(componentProvider)
	suite.componentController = componentController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	{
		routerGroup.GET("/component/:id", suite.componentController.GetComponent)
	}
	suite.router = r
}

func (suite *ComponentControllerTestSuite) TearDownTest() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentControllerTestSuite) AddSampleComponent() error {
	db, _ := testhelper.InitDBConnection(suite.mySQLContainer.ConnStr)
	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	opTime, _ := time.Parse(time.DateTime, operationTime)

	component := &model.K8sCrdComponentModel{
		ComponentName: "test1",
		CrdClusterID:  1,
		Status:        "CREATED",
		Description:   "just for test",
		CreatedBy:     "admin",
		CreatedAt:     types.JSONDatetime(opTime),
		UpdatedBy:     "admin",
		UpdatedAt:     types.JSONDatetime(opTime),
	}
	addedComponent, err := dbAccess.Create(component)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("Add Sample component %v\n", addedComponent)
	return nil
}

func (suite *ComponentControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sCrdComponent, &model.K8sCrdComponentModel{})
}

func (suite *ComponentControllerTestSuite) TestGetComponent() {
	t := suite.T()
	if err := suite.AddSampleComponent(); err != nil {
		log.Fatal(err)
	}
	request, _ := http.NewRequest("GET", "/metadata/component/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"crdClusterId": 1,
			"componentName": "test1",
			"status": "CREATED",
			"description": "just for test",
			"createdBy": "admin",
			"createdAt": "2025-01-01 20:00:00",
			"updatedBy": "admin",
			"updatedAt": "2025-01-01 20:00:00"
		},
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func TestComponentControllerTestSuite(t *testing.T) {
	suite.Run(t, new(ComponentControllerTestSuite))
}
