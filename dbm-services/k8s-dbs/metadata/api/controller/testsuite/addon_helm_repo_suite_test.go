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

var addonHelmRepoRequest = vo.AddonHelmRepoRequest{
	RepoName:       "repo_name_01",
	RepoRepository: "repo_repository_01",
	RepoUsername:   "repo_username_01",
	RepoPassword:   "repo_password_01",
	ChartName:      "chart_name_01",
	ChartVersion:   "chart_version_01",
	BKAuth:         baseBKAuth,
}

type AddonHelmRepoControllerTestSuite struct {
	suite.Suite
	mySQLContainer          *testhelper.MySQLContainerWrapper
	addonHelmRepoController *controller.AddonHelmRepoController
	ctx                     context.Context
	router                  *gin.Engine
}

func (suite *AddonHelmRepoControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonHelmRepoDbAccess(db)
	addonProvider := provider.NewAddonHelmRepoProvider(dbAccess)
	addonHelmRepoController := controller.NewAddonHelmRepoController(addonProvider)
	suite.addonHelmRepoController = addonHelmRepoController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	{
		routerGroup.POST("/addon_helm_repo", suite.addonHelmRepoController.CreateAddonHelmRepo)
		routerGroup.GET("/addon_helm_repo/:id", suite.addonHelmRepoController.GetAddonHelmRepoByID)
	}
	suite.router = r
}

func (suite *AddonHelmRepoControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonHelmRepoControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonHelmRepo, &model.AddonHelmRepoModel{})
}

func TestAddonHelmRepoController(t *testing.T) {
	suite.Run(t, new(AddonHelmRepoControllerTestSuite))
}

func (suite *AddonHelmRepoControllerTestSuite) TestCreateAddonHelmRepo() {
	t := suite.T()
	jsonData, _ := json.Marshal(addonHelmRepoRequest)
	request, _ := http.NewRequest("POST", "/metadata/addon_helm_repo", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "id": 1,
		  "repoName": "repo_name_01",
		  "repoRepository": "repo_repository_01",
		  "repoUsername": "repo_username_01",
		  "repoPassword": "repo_password_01",
		  "chartName": "chart_name_01",
		  "chartVersion": "chart_version_01",
          "createdBy":"admin",
          "updatedBy":"admin"
		},
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonHelmRepoControllerTestSuite) TestGetAddonHelmRepoByID() {
	t := suite.T()
	createMoreAddonHelmRepo(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/addon_helm_repo/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		  "id": 1,
		  "repoName": "repo_name_01",
		  "repoRepository": "repo_repository_01",
		  "repoUsername": "repo_username_01",
		  "repoPassword": "repo_password_01",
		  "chartName": "chart_name_01",
		  "chartVersion": "chart_version_01",
          "createdBy":"admin",
          "updatedBy":"admin"
		},
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
