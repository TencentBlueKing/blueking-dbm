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

var addonTopologyRequest = vo.AddonTopologyRequest{
	AddonName:     "addon_name_01",
	AddonCategory: "addon_category_01",
	AddonType:     "addon_type_01",
	AddonVersion:  "addon_version_01",
	TopologyName:  "topology_name_01",
	TopologyAlias: "topology_alias_01",
	IsDefault:     true,
	Components:    "{\"component1\": \"version1\", \"component2\": \"version2\"}",
	Relations:     "{\"relation1\": \"component1\", \"relation2\": \"component2\"}",
	Active:        true,
	Description:   "description_01",
	BKAuth:        baseBKAuth,
}

type AddonTopologyControllerTestSuite struct {
	suite.Suite
	mySQLContainer          *testhelper.MySQLContainerWrapper
	addonTopologyController *controller.AddonTopologyController
	ctx                     context.Context
	router                  *gin.Engine
}

func (suite *AddonTopologyControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonTopologyDbAccess(db)
	addonProvider := provider.NewAddonTopologyProvider(dbAccess)
	addonTopologyController := controller.NewAddonTopologyController(addonProvider)
	suite.addonTopologyController = addonTopologyController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/addon_topology")
	{
		routerGroup.POST("", suite.addonTopologyController.Create)
		routerGroup.GET("/:id", suite.addonTopologyController.GetByID)
		routerGroup.GET("", suite.addonTopologyController.GetByParams)
	}
	suite.router = r
}

func (suite *AddonTopologyControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonTopologyControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonTopology, &model.AddonTopologyModel{})
}

func TestAddonTopologyController(t *testing.T) {
	suite.Run(t, new(AddonTopologyControllerTestSuite))
}

func (suite *AddonTopologyControllerTestSuite) TestCreate() {
	t := suite.T()
	jsonData, _ := json.Marshal(addonTopologyRequest)
	request, _ := http.NewRequest("POST", "/metadata/addon_topology", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "addon_name":     "addon_name_01",
		  "addon_category": "addon_category_01",
		  "addon_type":     "addon_type_01",
		  "addon_version":  "addon_version_01",
		  "topology_name":  "topology_name_01",
		  "topology_alias": "topology_alias_01",
		  "is_default":     true,
		  "components":    "{\"component1\": \"version1\", \"component2\": \"version2\"}",
		  "relations":     "{\"relation1\": \"component1\", \"relation2\": \"component2\"}",
		  "active":        true,
		  "description":   "description_01",
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

func (suite *AddonTopologyControllerTestSuite) TestGetByID() {
	t := suite.T()
	createMoreAddonTopology(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/addon_topology/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "addon_name":     "addon_name_01",
		  "addon_category": "addon_category_01",
		  "addon_type":     "addon_type_01",
		  "addon_version":  "addon_version_01",
		  "topology_name":  "topology_name_01",
		  "topology_alias": "topology_alias_01",
		  "is_default":     true,
		  "components":    "{\"component1\": \"version1\", \"component2\": \"version2\"}",
		  "relations":     "{\"relation1\": \"component1\", \"relation2\": \"component2\"}",
		  "active":        true,
		  "description":   "description_01",
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

func (suite *AddonTopologyControllerTestSuite) TestGetParams() {
	t := suite.T()
	createMoreAddonTopology(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/addon_topology?addon_type=addon_type_01", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": [
		{
		  "addon_name":     "addon_name_01",
		  "addon_category": "addon_category_01",
		  "addon_type":     "addon_type_01",
		  "addon_version":  "addon_version_01",
		  "topology_name":  "topology_name_01",
		  "topology_alias": "topology_alias_01",
		  "is_default":     true,
		  "components":    "{\"component1\": \"version1\", \"component2\": \"version2\"}",
		  "relations":     "{\"relation1\": \"component1\", \"relation2\": \"component2\"}",
		  "active":        true,
		  "description":   "description_01",
		  "id": 1,
		  "createdBy": "admin",
		  "updatedBy": "admin"
		},
		{
		  "addon_name":     "addon_name_01",
		  "addon_category": "addon_category_01",
		  "addon_type":     "addon_type_01",
		  "addon_version":  "addon_version_01",
		  "topology_name":  "topology_name_01",
		  "topology_alias": "topology_alias_01",
		  "is_default":     true,
		  "components":    "{\"component1\": \"version1\", \"component2\": \"version2\"}",
		  "relations":     "{\"relation1\": \"component1\", \"relation2\": \"component2\"}",
		  "active":        true,
		  "description":   "description_01",
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
