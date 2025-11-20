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

type K8sClusterAddonsControllerTestSuite struct {
	suite.Suite
	mySQLContainer             *testhelper.MySQLContainerWrapper
	k8sClusterAddonsController *controller.K8sClusterAddonsController
	ctx                        context.Context
	router                     *gin.Engine
}

func (suite *K8sClusterAddonsControllerTestSuite) SetupSuite() {
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
	kcaDbAccess := dbaccess.NewK8sClusterAddonsDbAccess(db)
	saDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	k8sClusterAddonsProvider := provider.NewK8sClusterAddonsProvider(kcaDbAccess, saDbAccess)
	k8sClusterAddonsController := controller.NewK8sClusterAddonsController(k8sClusterAddonsProvider)
	suite.k8sClusterAddonsController = k8sClusterAddonsController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/k8s_cluster_addons")
	{
		routerGroup.GET("/:id", suite.k8sClusterAddonsController.GetAddon)
		routerGroup.GET("", suite.k8sClusterAddonsController.GetAddonsByClusterName)
	}
	suite.router = r
}

func (suite *K8sClusterAddonsControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *K8sClusterAddonsControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sClusterAddons, &model.K8sClusterAddonsModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sCrdStorageAddon, &model.K8sCrdStorageAddonModel{})
}

func TestK8sClusterAddonsController(t *testing.T) {
	suite.Run(t, new(K8sClusterAddonsControllerTestSuite))
}

func (suite *K8sClusterAddonsControllerTestSuite) TestGetAddon() {
	t := suite.T()
	createMoreK8sClusterAddons(suite.mySQLContainer, 1)

	request, _ := http.NewRequest("GET", "/metadata/k8s_cluster_addons/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)

	expected := `
	{
	  "code": 200,
	  "data": {
		"addonId": 1,
		"createdBy": "admin",
		"id": 1,
		"k8sClusterName": "test-cluster",
		"storageAddon": {
		  "active": true,
		  "addonCategory": "storage",
		  "addonName": "test-addon",
		  "addonType": "mysql",
		  "addonVersion": "1.0.0",
		  "createdBy": "admin",
		  "description": "Test addon",
		  "id": 1,
		  "recommendedVersion": "1.0.0",
		  "recommendedAcVersion": "1.0.0",
		  "supportedVersions": ["1.0.0"],
		  "supportedAcVersions": ["1.0.0"],
		  "topologies": [{"name":"cluster","isDefault":true}],
		  "releases": [{"version":"1.0.0"}],
		  "updatedBy": "admin"
		},
		"updatedBy": "admin"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *K8sClusterAddonsControllerTestSuite) TestGetAddonsByClusterName() {
	t := suite.T()
	createMoreK8sClusterAddons(suite.mySQLContainer, 1)

	request, _ := http.NewRequest("GET", "/metadata/k8s_cluster_addons?k8sClusterName=test-cluster", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)

	expected := `
	{
	  "code": 200,
	  "data": [
		{
		  "addonId": 1,
		  "createdBy": "admin",
		  "id": 1,
		  "k8sClusterName": "test-cluster",
		  "storageAddon": {
			"active": true,
			"addonCategory": "storage",
			"addonName": "test-addon",
			"addonType": "mysql",
			"addonVersion": "1.0.0",
			"createdBy": "admin",
			"description": "Test addon",
			"id": 1,
			"recommendedVersion": "1.0.0",
			"recommendedAcVersion": "1.0.0",
			"supportedVersions": ["1.0.0"],
			"supportedAcVersions": ["1.0.0"],
			"topologies": [{"name":"cluster","isDefault":true}],
			"releases": [{"version":"1.0.0"}],
			"updatedBy": "admin"
		  },
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
