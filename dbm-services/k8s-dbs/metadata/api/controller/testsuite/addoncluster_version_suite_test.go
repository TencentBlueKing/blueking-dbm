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

var addonClusterVersionRequest = vo.AddonClusterVersionRequest{
	AddonID:          uint64(1),
	Version:          "1.0.0",
	AddonClusterName: "addon_cluster_name_01",
	Active:           true,
	Description:      "addon_cluster_version_description_01",
	BKAuth:           baseBKAuth,
}

type AddonClusterVersionControllerTestSuite struct {
	suite.Suite
	mySQLContainer                *testhelper.MySQLContainerWrapper
	addonClusterVersionController *controller.AddonClusterVersionController
	ctx                           context.Context
	router                        *gin.Engine
}

func (suite *AddonClusterVersionControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonClusterVersionDbAccess(db)
	addonProvider := provider.NewAddonClusterVersionProvider(dbAccess)
	addonClusterVersionController := controller.NewAddonClusterVersionController(addonProvider)
	suite.addonClusterVersionController = addonClusterVersionController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/addoncluster_version")
	{
		routerGroup.POST("", suite.addonClusterVersionController.CreateAcVersion)
		routerGroup.GET("/:id", suite.addonClusterVersionController.GetAcVersion)
		routerGroup.PUT("/:id", suite.addonClusterVersionController.UpdateAcVersion)
		routerGroup.DELETE("/:id", suite.addonClusterVersionController.DeleteAcVersion)
		routerGroup.GET("", suite.addonClusterVersionController.ListAcVersions)
	}
	suite.router = r
}

func (suite *AddonClusterVersionControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterVersionControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonClusterVersion, &model.AddonClusterVersionModel{})
}

func TestAddonClusterVersionController(t *testing.T) {
	suite.Run(t, new(AddonClusterVersionControllerTestSuite))
}

func (suite *AddonClusterVersionControllerTestSuite) TestCreateAvVersion() {
	t := suite.T()
	jsonData, _ := json.Marshal(addonClusterVersionRequest)
	request, _ := http.NewRequest("POST", "/metadata/addoncluster_version", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"active": true,
		"addonClusterName": "addon_cluster_name_01",
		"addonId": 1,
		"createdBy": "",
		"description": "addon_cluster_version_description_01",
		"id": 1,
		"updatedBy": "",
		"version": "1.0.0"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonClusterVersionControllerTestSuite) TestGetAvVersion() {
	t := suite.T()
	createMoreAddonClusterVersion(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/addoncluster_version/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"active": true,
		"addonClusterName": "addon_cluster_name_01",
		"addonId": 1,
		"createdBy": "admin",
		"description": "addon_cluster_version_description_01",
		"id": 1,
		"updatedBy": "admin",
		"version": "1.0.0"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonClusterVersionControllerTestSuite) TestUpdateAvVersion() {
	t := suite.T()
	createMoreAddonClusterVersion(suite.mySQLContainer, 1)
	addonClusterVersionRequest.Active = false
	jsonData, _ := json.Marshal(addonClusterVersionRequest)
	request, _ := http.NewRequest("PUT", "/metadata/addoncluster_version/1", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"rows": 1
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonClusterVersionControllerTestSuite) TestDeleteAvVersion() {
	t := suite.T()
	createMoreAddonClusterVersion(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("DELETE", "/metadata/addoncluster_version/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"rows": 1
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonClusterVersionControllerTestSuite) TestListAvVersion() {
	t := suite.T()
	createMoreAddonClusterVersion(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/addoncluster_version?size=10", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": [
		{
		  "active": true,
		  "addonClusterName": "addon_cluster_name_01",
		  "addonId": 1,
		  "createdBy": "admin",
		  "description": "addon_cluster_version_description_01",
		  "id": 1,
		  "updatedBy": "admin",
		  "version": "1.0.0"
		  },
		{
		  "active": true,
		  "addonClusterName": "addon_cluster_name_01",
		  "addonId": 1,
		  "createdBy": "admin",
		  "description": "addon_cluster_version_description_01",
		  "id": 2,
		  "updatedBy": "admin",
		  "version": "1.0.0"
		  }
	  ],
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
