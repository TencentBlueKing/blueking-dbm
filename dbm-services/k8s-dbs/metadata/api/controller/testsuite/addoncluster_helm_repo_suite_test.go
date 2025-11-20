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

var addonClusterHelmRepoRequest = vo.AddonClusterHelmRepoRequest{
	RepoName:       "repo_name_01",
	RepoRepository: "repo_repository_01",
	RepoUsername:   "repo_username_01",
	RepoPassword:   "repo_password_01",
	ChartName:      "chart_name_01",
	ChartVersion:   "chart_version_01",
	BKAuth:         baseBKAuth,
}

var addonClusterHelmRepoParam = map[string]interface{}{
	"chartName": "chart_name_01",
}

type AddonClusterHelmRepoControllerTestSuite struct {
	suite.Suite
	mySQLContainer            *testhelper.MySQLContainerWrapper
	clusterHelmRepoController *controller.ClusterHelmRepoController
	ctx                       context.Context
	router                    *gin.Engine
}

func (suite *AddonClusterHelmRepoControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonClusterHelmRepoDbAccess(db)
	addonProvider := provider.NewAddonClusterHelmRepoProvider(dbAccess)
	clusterHelmRepoController := controller.NewClusterHelmRepoController(addonProvider)
	suite.clusterHelmRepoController = clusterHelmRepoController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/addoncluster_helm_repo")
	{
		routerGroup.POST("", suite.clusterHelmRepoController.CreateClusterHelmRepo)
		routerGroup.GET("/:id", suite.clusterHelmRepoController.GetClusterHelmRepoByID)
	}
	suite.router = r
}

func (suite *AddonClusterHelmRepoControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonClusterHelmRepoControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonClusterHelmRepo, &model.AddonClusterHelmRepoModel{})
}

func TestAddonClusterHelmRepoController(t *testing.T) {
	suite.Run(t, new(AddonClusterHelmRepoControllerTestSuite))
}

func (suite *AddonClusterHelmRepoControllerTestSuite) TestCreateClusterHelmRepo() {
	t := suite.T()
	jsonData, _ := json.Marshal(addonClusterHelmRepoRequest)
	request, _ := http.NewRequest("POST", "/metadata/addoncluster_helm_repo", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"chartName": "chart_name_01",
		"chartVersion": "chart_version_01",
		"createdBy": "admin",
		"id": 1,
		"repoName": "repo_name_01",
		"repoPassword": "repo_password_01",
		"repoRepository": "repo_repository_01",
		"repoUsername": "repo_username_01",
		"updatedBy": "admin"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonClusterHelmRepoControllerTestSuite) TestGetClusterHelmRepoByID() {
	t := suite.T()
	createMoreAddonClusterHelmRepo(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/addoncluster_helm_repo/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"chartName": "chart_name_01",
		"chartVersion": "chart_version_01",
		"createdBy": "admin",
		"id": 1,
		"repoName": "repo_name_01",
		"repoPassword": "repo_password_01",
		"repoRepository": "repo_repository_01",
		"repoUsername": "repo_username_01",
		"updatedBy": "admin"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
