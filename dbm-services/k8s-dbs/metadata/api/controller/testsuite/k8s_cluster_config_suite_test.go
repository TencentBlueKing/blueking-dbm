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

var k8sClusterConfigRequest = vo.K8sClusterConfigRequest{
	ClusterName:  "test-k8s-cluster",
	APIServerURL: "https://www.example.com",
	CACert:       "test-ca-cert",
	ClientCert:   "test-client-cert",
	ClientKey:    "test-client-key",
	Token:        "test-token",
	Username:     "test-user",
	Password:     "test-password",
	Description:  "测试K8s集群配置",
	BKAuth:       baseBKAuth,
}

type K8sClusterConfigControllerTestSuite struct {
	suite.Suite
	mySQLContainer             *testhelper.MySQLContainerWrapper
	k8sClusterConfigController *controller.K8sClusterConfigController
	ctx                        context.Context
	router                     *gin.Engine
}

func (suite *K8sClusterConfigControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := provider.NewK8sClusterConfigProvider(dbAccess)
	k8sClusterConfigController := controller.NewK8sClusterConfigController(k8sClusterConfigProvider)
	suite.k8sClusterConfigController = k8sClusterConfigController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/k8s_cluster_config")
	{
		routerGroup.DELETE("/:id", suite.k8sClusterConfigController.DeleteK8sClusterConfig)
		routerGroup.POST("", suite.k8sClusterConfigController.CreateK8sClusterConfig)
		routerGroup.PUT("/:id", suite.k8sClusterConfigController.UpdateK8sClusterConfig)
		routerGroup.GET("/regions", suite.k8sClusterConfigController.GetRegionsByVisibility)
	}
	suite.router = r
}

func (suite *K8sClusterConfigControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *K8sClusterConfigControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sClusterConfig, &model.K8sClusterConfigModel{})
}

func TestK8sClusterConfigController(t *testing.T) {
	suite.Run(t, new(K8sClusterConfigControllerTestSuite))
}

func (suite *K8sClusterConfigControllerTestSuite) TestCreateK8sClusterConfig() {
	t := suite.T()
	jsonData, _ := json.Marshal(k8sClusterConfigRequest)
	request, _ := http.NewRequest("POST", "/metadata/k8s_cluster_config", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"active": true,
		"apiServerUrl": "https://www.example.com",
		"caCert": "test-ca-cert",
		"clientCert": "test-client-cert",
		"clientKey": "test-client-key",
		"clusterName": "test-k8s-cluster",
		"createdBy": "",
		"description": "测试K8s集群配置",
		"id": 1,
		"isPublic": true,
		"password": "test-password",
		"provider": "",
		"regionCode": "",
		"regionName": "",
		"token": "test-token",
		"updatedBy": "",
		"username": "test-user"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *K8sClusterConfigControllerTestSuite) TestUpdateK8sClusterConfig() {
	t := suite.T()
	createMoreK8sClusterConfig(suite.mySQLContainer, 1)

	updateRequest := k8sClusterConfigRequest
	updateRequest.Description = "更新后的K8s集群配置"
	jsonData, _ := json.Marshal(updateRequest)
	request, _ := http.NewRequest("PUT", "/metadata/k8s_cluster_config/1", bytes.NewReader(jsonData))
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
	assert.JSONEq(t, expected, w.Body.String())
}

func (suite *K8sClusterConfigControllerTestSuite) TestDeleteK8sClusterConfig() {
	t := suite.T()
	createMoreK8sClusterConfig(suite.mySQLContainer, 1)

	request, _ := http.NewRequest("DELETE", "/metadata/k8s_cluster_config/1", nil)
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
	assert.JSONEq(t, expected, w.Body.String())
}

func (suite *K8sClusterConfigControllerTestSuite) TestGetRegionsByVisibility() {
	t := suite.T()
	createMoreK8sClusterConfig(suite.mySQLContainer, 2)

	request, _ := http.NewRequest("GET", "/metadata/k8s_cluster_config/regions?isPublic=true", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)

	expected := `
	{
	  "code": 200,
	  "data": [
		{
		  "clusterName": "test-k8s-cluster",
		  "isPublic": true,
		  "provider": "test-provider",
		  "regionCode": "test-region-code",
		  "regionName": "test-region"
		},
		{
		  "clusterName": "test-k8s-cluster",
		  "isPublic": true,
		  "provider": "test-provider",
		  "regionCode": "test-region-code",
		  "regionName": "test-region"
		}
	  ],
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}
