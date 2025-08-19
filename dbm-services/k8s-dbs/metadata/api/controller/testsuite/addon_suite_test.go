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

var addonRequest = vo.AddonRequest{
	AddonName:            "addon_name_01",
	AddonCategory:        "addon_category_01",
	AddonType:            "addon_type_01",
	AddonVersion:         "addon_version_01",
	RecommendedVersion:   "recommended_version_01",
	SupportedVersions:    `["supported_versions_01", "supported_versions_02"]`,
	RecommendedAcVersion: "recommended_ac_version_01",
	SupportedAcVersions:  `["supported_ac_versions_01", "supported_ac_versions_02"]`,
	Topologies:           `[{"name": "topology_01"}]`,
	Releases:             `[{"version": "1.0"}]`,
	Description:          "description_01",
	BKAuth:               baseBKAuth,
}

type AddonControllerTestSuite struct {
	suite.Suite
	mySQLContainer  *testhelper.MySQLContainerWrapper
	addonController *controller.AddonController
	ctx             context.Context
	router          *gin.Engine
}

func (suite *AddonControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	addonProvider := provider.NewK8sCrdStorageAddonProvider(dbAccess)
	addonController := controller.NewAddonController(addonProvider)
	suite.addonController = addonController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	{
		routerGroup.POST("/addon", suite.addonController.CreateAddon)
		routerGroup.PUT("/addon/:id", suite.addonController.UpdateAddon)
		routerGroup.DELETE("/addon/:id", suite.addonController.DeleteAddon)
		routerGroup.GET("/addon/:id", suite.addonController.GetAddon)
		routerGroup.GET("/addon/versions", suite.addonController.GetVersions)
		routerGroup.GET("/addon", suite.addonController.ListAddons)
	}
	suite.router = r
}

func (suite *AddonControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sCrdStorageAddon, &model.K8sCrdStorageAddonModel{})
}

func TestAddonController(t *testing.T) {
	suite.Run(t, new(AddonControllerTestSuite))
}

func (suite *AddonControllerTestSuite) TestCreateAddon() {
	t := suite.T()
	jsonData, _ := json.Marshal(addonRequest)
	request, _ := http.NewRequest("POST", "/metadata/addon", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "addonName": "addon_name_01",
		  "addonCategory": "addon_category_01",
		  "addonType": "addon_type_01",
		  "addonVersion": "addon_version_01",
		  "recommendedVersion": "recommended_version_01",
		  "supportedVersions": ["supported_versions_01", "supported_versions_02"],
		  "recommendedAcVersion": "recommended_ac_version_01",
		  "supportedAcVersions": ["supported_ac_versions_01", "supported_ac_versions_02"],
		  "topologies": [{"name": "topology_01"}],
		  "releases": [{"version": "1.0"}],
		  "description": "description_01",
		  "active": true,
		  "id": 1,
		  "createdBy": "admin",
		  "updatedBy": "admin"
		},
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonControllerTestSuite) TestUpdateAddon() {
	t := suite.T()
	createMoreAddon(suite.mySQLContainer, 3)
	addonRequest.AddonName = "addon_name_01_updated"
	jsonData, _ := json.Marshal(addonRequest)
	request, _ := http.NewRequest("PUT", "/metadata/addon/3", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "rows": 1
		},
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func (suite *AddonControllerTestSuite) TestDeleteAddon() {
	t := suite.T()
	createMoreAddon(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("DELETE", "/metadata/addon/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "rows": 1
		},
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func (suite *AddonControllerTestSuite) TestGetAddon() {
	t := suite.T()
	createMoreAddon(suite.mySQLContainer, 4)
	request, _ := http.NewRequest("GET", "/metadata/addon/4", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "addonName": "addon_name_01",
		  "addonCategory": "addon_category_01",
		  "addonType": "addon_type_01",
		  "addonVersion": "addon_version_01",
		  "recommendedVersion": "recommended_version_01",
		  "supportedVersions": ["supported_versions_01", "supported_versions_02"],
		  "recommendedAcVersion": "recommended_ac_version_01",
		  "supportedAcVersions": ["supported_ac_versions_01", "supported_ac_versions_02"],
		  "topologies": [{"name": "topology_01"}],
		  "releases": [{"version": "1.0"}],
		  "description": "description_01",
		  "active": true,
		  "id": 4,
		  "createdBy": "admin",
		  "updatedBy": "admin"
		},
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonControllerTestSuite) TestGetVersions() {
	t := suite.T()
	createMoreAddon(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/addon/versions?addon_type=addon_type_01", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": [
		{
			"addonVersion": "addon_version_01",
			"supportedVersions": ["supported_versions_01", "supported_versions_02"]
		},
		{
			"addonVersion": "addon_version_01",
			"supportedVersions": ["supported_versions_01", "supported_versions_02"]
		}
	  ],
	  "message": "success",
	  "error": null
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonControllerTestSuite) TestListAddon() {
	t := suite.T()
	createMoreAddon(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/addon?size=2", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": [
		{
		  "addonName": "addon_name_01",
		  "addonCategory": "addon_category_01",
		  "addonType": "addon_type_01",
		  "addonVersion": "addon_version_01",
		  "recommendedVersion": "recommended_version_01",
		  "supportedVersions": ["supported_versions_01", "supported_versions_02"],
		  "recommendedAcVersion": "recommended_ac_version_01",
		  "supportedAcVersions": ["supported_ac_versions_01", "supported_ac_versions_02"],
		  "topologies": [{"name": "topology_01"}],
		  "releases": [{"version": "1.0"}],
		  "description": "description_01",
		  "active": true,
		  "id": 1,
		  "createdBy": "admin",
		  "updatedBy": "admin"
		},
		{
		  "addonName": "addon_name_01",
		  "addonCategory": "addon_category_01",
		  "addonType": "addon_type_01",
		  "addonVersion": "addon_version_01",
		  "recommendedVersion": "recommended_version_01",
		  "supportedVersions": ["supported_versions_01", "supported_versions_02"],
		  "recommendedAcVersion": "recommended_ac_version_01",
		  "supportedAcVersions": ["supported_ac_versions_01", "supported_ac_versions_02"],
		  "topologies": [{"name": "topology_01"}],
		  "releases": [{"version": "1.0"}],
		  "description": "description_01",
		  "active": true,
		  "id": 2,
		  "createdBy": "admin",
		  "updatedBy": "admin"
		}
	  ],
	  "message": "success",
	  "error": null
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
