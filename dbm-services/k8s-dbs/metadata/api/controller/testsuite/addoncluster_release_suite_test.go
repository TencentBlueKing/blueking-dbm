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

type AddonClusterReleaseControllerTestSuite struct {
	suite.Suite
	mySQLContainer           *testhelper.MySQLContainerWrapper
	clusterReleaseController *controller.ClusterReleaseController
	ctx                      context.Context
	router                   *gin.Engine
}

func (suite *AddonClusterReleaseControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonClusterReleaseDbAccess(db)
	addonProvider := provider.NewAddonClusterReleaseProvider(dbAccess)
	clusterReleaseController := controller.NewClusterReleaseController(addonProvider)
	suite.clusterReleaseController = clusterReleaseController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/cluster_release")
	{
		routerGroup.GET("/id/:id", suite.clusterReleaseController.GetClusterRelease)
		routerGroup.GET("/name/:releaseName/namespace/:namespace", suite.clusterReleaseController.GetClusterReleaseByParam)
	}
	suite.router = r
}

func (suite *AddonClusterReleaseControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterReleaseControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonClusterRelease, &model.AddonClusterReleaseModel{})
}

func TestAddonClusterReleaseController(t *testing.T) {
	suite.Run(t, new(AddonClusterReleaseControllerTestSuite))
}

func (suite *AddonClusterReleaseControllerTestSuite) TestGetClusterRelease() {
	t := suite.T()
	createMoreAddonClusterRelease(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/cluster_release/id/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"chartName": "chart_name_01",
		"chartValues": null,
		"chartVersion": "chart_version_01",
		"createdBy": "admin",
		"id": 1,
		"k8sClusterConfigId": 1,
		"namespace": "namespace_01",
		"releaseName": "release_name_01",
		"repoName": "repo_name_01",
		"repoRepository": "repo_repository_01",
		"updatedBy": "admin"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonClusterReleaseControllerTestSuite) TestGetClusterReleaseByParam() {
	t := suite.T()
	createMoreAddonClusterRelease(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/cluster_release/name/release_name_01/namespace/namespace_01", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"chartName": "chart_name_01",
		"chartValues": {},
		"chartVersion": "chart_version_01",
		"createdBy": "admin",
		"id": 1,
		"k8sClusterConfigId": 1,
		"namespace": "namespace_01",
		"releaseName": "release_name_01",
		"repoName": "repo_name_01",
		"repoRepository": "repo_repository_01",
		"updatedBy": "admin"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
