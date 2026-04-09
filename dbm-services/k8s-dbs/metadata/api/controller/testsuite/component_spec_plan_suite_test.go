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
	"net/http"
	"net/http/httptest"

	commconst "k8s-dbs/common/constant"
	"k8s-dbs/metadata/api/controller"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	metareq "k8s-dbs/metadata/vo/request"
	"log"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var componentSpecPlanVOCreate = &metareq.ComponentSpecPlanRequest{
	AddonSpecPlanID: 1,
	ComponentName:   "mysql",
	CPUCores:        reqIntPtr(4),
	MemoryGb:        reqIntPtr(8),
	DiskSizeGb:      reqIntPtr(100),
	BKAdditional:    baseBKAdditional,
}

func reqIntPtr(i int) *int {
	return &i
}

type ComponentSpecPlanControllerTestSuite struct {
	suite.Suite
	mySqlContainer              *testhelper.MySQLContainerWrapper
	router                      *gin.Engine
	componentSpecPlanController *controller.ComponentSpecPlanController
	ctx                         context.Context
}

func (suite *ComponentSpecPlanControllerTestSuite) SetupSuite() {
	gin.SetMode(gin.TestMode)
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
	suite.componentSpecPlanController = controller.NewComponentSpecPlanController(
		provider.GetComponentSpecPlanProvider(dbaccess.GetComponentSpecPlanDbAccess(db)),
	)

	suite.router = gin.New()
	api := suite.router.Group("/api/metadata")
	{
		api.GET("/component-spec-plans", suite.componentSpecPlanController.ListComponentSpecPlans)
		api.GET("/component-spec-plans/:id", suite.componentSpecPlanController.GetComponentSpecPlan)
		api.POST("/component-spec-plans", suite.componentSpecPlanController.CreateComponentSpecPlan)
		api.PUT("/component-spec-plans/:id", suite.componentSpecPlanController.UpdateComponentSpecPlan)
		api.DELETE("/component-spec-plans/:id", suite.componentSpecPlanController.DeleteComponentSpecPlan)
	}
}

func (suite *ComponentSpecPlanControllerTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentSpecPlanControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbComponentSpecPlan, &model.ComponentSpecPlanModel{})
}

func TestComponentSpecPlanController(t *testing.T) {
	suite.Run(t, new(ComponentSpecPlanControllerTestSuite))
}

func (suite *ComponentSpecPlanControllerTestSuite) TestCreateAndGet() {
	t := suite.T()

	// Create
	body, _ := json.Marshal(componentSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/component-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var createResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &createResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(createResp["code"].(float64)))

	// Get by ID
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/api/metadata/component-spec-plans/1", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var getResp map[string]interface{}
	err = json.Unmarshal(w.Body.Bytes(), &getResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(getResp["code"].(float64)))
}

func (suite *ComponentSpecPlanControllerTestSuite) TestUpdate() {
	t := suite.T()

	// Create first
	body, _ := json.Marshal(componentSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/component-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	// Update
	updateReq := componentSpecPlanVOCreate
	newCPU := 8
	updateReq.CPUCores = &newCPU
	body, _ = json.Marshal(updateReq)
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("PUT", "/api/metadata/component-spec-plans/1", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var updateResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &updateResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(updateResp["code"].(float64)))
}

func (suite *ComponentSpecPlanControllerTestSuite) TestDelete() {
	t := suite.T()

	// Create first
	body, _ := json.Marshal(componentSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/component-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	// Delete
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/api/metadata/component-spec-plans/1", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var deleteResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &deleteResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(deleteResp["code"].(float64)))
}

func (suite *ComponentSpecPlanControllerTestSuite) TestList() {
	t := suite.T()

	// Create first
	body, _ := json.Marshal(componentSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/component-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	// List
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/api/metadata/component-spec-plans", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var listResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &listResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(listResp["code"].(float64)))
}
