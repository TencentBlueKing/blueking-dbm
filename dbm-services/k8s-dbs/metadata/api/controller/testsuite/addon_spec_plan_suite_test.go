/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with License.

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

var addonSpecPlanVOCreate = &metareq.AddonSpecPlanRequest{
	AddonID:        1,
	AddonTopology:  "standalone",
	SpecLevel:      "basic",
	SpecLevelAlias: "基础版",
	BKAdditional:   baseBKAdditional,
}

type AddonSpecPlanControllerTestSuite struct {
	suite.Suite
	mySqlContainer          *testhelper.MySQLContainerWrapper
	router                  *gin.Engine
	addonSpecPlanController *controller.AddonSpecPlanController
	ctx                     context.Context
}

func (suite *AddonSpecPlanControllerTestSuite) SetupSuite() {
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
	specPlanProviderBuilder := provider.AddonSpecPlanProviderBuilder{}
	specPlanProvider := provider.GetAddonSpecPlanProvider(
		specPlanProviderBuilder.WithSpecPlanDbAccess(dbaccess.GetAddonSpecPlanDbAccess(db)),
		specPlanProviderBuilder.WithStorageAddonDbAccess(dbaccess.GetStorageAddonDbAccess(db)),
		specPlanProviderBuilder.WithComponentSpecPlanDbAccess(dbaccess.GetComponentSpecPlanDbAccess(db)),
	)
	suite.addonSpecPlanController = controller.NewAddonSpecPlanController(specPlanProvider)

	suite.router = gin.New()
	api := suite.router.Group("/api/metadata")
	{
		api.GET("/addon-spec-plans", suite.addonSpecPlanController.ListAddonSpecPlans)
		api.GET("/addon-spec-plans/detail", suite.addonSpecPlanController.GetAddonSpecPlan)
		api.POST("/addon-spec-plans", suite.addonSpecPlanController.CreateAddonSpecPlan)
		api.PUT("/addon-spec-plans/:id", suite.addonSpecPlanController.UpdateAddonSpecPlan)
		api.DELETE("/addon-spec-plans/:id", suite.addonSpecPlanController.DeleteAddonSpecPlan)
	}
}

func (suite *AddonSpecPlanControllerTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonSpecPlanControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonSpecPlan, &model.AddonSpecPlanModel{})
}

func TestAddonSpecPlanController(t *testing.T) {
	suite.Run(t, new(AddonSpecPlanControllerTestSuite))
}

func (suite *AddonSpecPlanControllerTestSuite) TestCreateAndGet() {
	t := suite.T()
	// Create
	body, _ := json.Marshal(addonSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/addon-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var createResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &createResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(createResp["code"].(float64)))

	// Get detail by query params
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/api/metadata/addon-spec-plans/detail", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var getResp map[string]interface{}
	err = json.Unmarshal(w.Body.Bytes(), &getResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(getResp["code"].(float64)))
}

func (suite *AddonSpecPlanControllerTestSuite) TestUpdate() {
	t := suite.T()

	// Create first
	body, _ := json.Marshal(addonSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/addon-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	// Update
	updateReq := addonSpecPlanVOCreate
	updateReq.SpecLevel = "premium"
	body, _ = json.Marshal(updateReq)
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("PUT", "/api/metadata/addon-spec-plans/1", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var updateResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &updateResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(updateResp["code"].(float64)))
}

func (suite *AddonSpecPlanControllerTestSuite) TestDelete() {
	t := suite.T()

	// Create first
	body, _ := json.Marshal(addonSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/addon-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	// Delete
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("DELETE", "/api/metadata/addon-spec-plans/1", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var deleteResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &deleteResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(deleteResp["code"].(float64)))
}

func (suite *AddonSpecPlanControllerTestSuite) TestList() {
	t := suite.T()

	// Create first
	body, _ := json.Marshal(addonSpecPlanVOCreate)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/metadata/addon-spec-plans", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	// List
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/api/metadata/addon-spec-plans", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var listResp map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &listResp)
	assert.NoError(t, err)
	assert.Equal(t, commconst.Success, int(listResp["code"].(float64)))
}
