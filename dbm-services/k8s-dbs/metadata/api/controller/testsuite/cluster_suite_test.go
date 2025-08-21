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
	vo "k8s-dbs/metadata/vo/request"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var clusterRequest = vo.K8sCrdClusterRequest{
	AddonID:            1,
	K8sClusterConfigID: 1,
	RequestID:          "test-request-001",
	ClusterName:        "test-cluster",
	ClusterAlias:       "Test Cluster",
	Namespace:          "default",
	BkBizID:            1,
	BkBizName:          "测试业务",
	Description:        "just for test",
	CreatedBy:          "admin",
}

type ClusterControllerTestSuite struct {
	suite.Suite
	mySQLContainer    *testhelper.MySQLContainerWrapper
	clusterController *controller.ClusterController
	ctx               context.Context
	router            *gin.Engine
}

func (suite *ClusterControllerTestSuite) SetupSuite() {
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
	clusterDbAccess := dbaccess.NewCrdClusterDbAccess(db)
	addonDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := dbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sConfigDbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)
	addonTopologyDbAccess := dbaccess.NewAddonTopologyDbAccess(db)

	builder := &provider.K8sCrdClusterProviderBuilder{}
	clusterProvider, err := provider.NewK8sCrdClusterProvider(
		builder.WithClusterDbAccess(clusterDbAccess),
		builder.WithAddonDbAccess(addonDbAccess),
		builder.WithClusterTagDbAccess(clusterTagDbAccess),
		builder.WithK8sClusterConfigDbAccess(k8sConfigDbAccess),
		builder.WithAddonTopologyDbAccess(addonTopologyDbAccess),
	)
	if err != nil {
		log.Fatal(err)
	}
	clusterController := controller.NewClusterController(clusterProvider)
	suite.clusterController = clusterController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata/cluster")
	{
		routerGroup.GET("/:id", suite.clusterController.GetClusterInfo)
		routerGroup.GET("/topology/:id", suite.clusterController.GetClusterTopology)
		routerGroup.GET("/search", suite.clusterController.ListCluster)
	}
	suite.router = r
}

func (suite *ClusterControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sCrdCluster, &model.K8sCrdClusterModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sCrdStorageAddon, &model.K8sCrdStorageAddonModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sClusterConfig, &model.K8sClusterConfigModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbK8sCrdClusterTag, &model.K8sCrdClusterTagModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonTopology, &model.AddonTopologyModel{})
}

func TestClusterController(t *testing.T) {
	suite.Run(t, new(ClusterControllerTestSuite))
}

func (suite *ClusterControllerTestSuite) TestListCluster() {
	t := suite.T()
	createMoreCluster(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/cluster/search?size=10", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"count": 2,
		"result": [
		  {
			"addonClusterVersion": "",
			"addonInfo": {
			  "active": true,
			  "addonCategory": "storage",
			  "addonName": "test-storage-addon",
			  "addonType": "storage",
			  "addonVersion": "1.0.0",
			  "id": 1,
			  "topology": {
				"components": [],
				"description": "集群拓扑",
				"isDefault": true,
				"name": "cluster"
			  }
			},
			"bkAppAbbr": "",
			"bkAppCode": "",
			"bkBizId": 1,
			"bkBizName": "测试业务",
			"bkBizTitle": "[1]测试业务",
			"clusterAlias": "Test Cluster",
			"clusterName": "test-cluster",
			"createdBy": "admin",
			"description": "just for test",
			"id": 1,
			"k8sClusterConfig": {
			  "active": true,
			  "apiServerUrl": "https://www.example.com",
			  "caCert": "test-ca-cert",
			  "clientCert": "test-client-cert",
			  "clientKey": "test-client-key",
			  "clusterName": "test-k8s-cluster",
			  "createdBy": "admin",
			  "description": "测试K8s集群配置",
			  "id": 1,
			  "isPublic": true,
			  "password": "test-password",
			  "provider": "test-provider",
			  "regionCode": "test-region-code",
			  "regionName": "test-region",
			  "token": "test-token",
			  "updatedBy": "admin",
			  "username": "test-user"
			},
			"namespace": "default",
			"requestId": "",
			"serviceVersion": "",
			"status": "CREATED",
			"tags": [],
			"terminationPolicy": "",
			"topoName": "cluster",
			"topoNameAlias": "",
			"updatedBy": "admin"
		  },
		  {
			"addonClusterVersion": "",
			"addonInfo": {
			  "active": true,
			  "addonCategory": "storage",
			  "addonName": "test-storage-addon",
			  "addonType": "storage",
			  "addonVersion": "1.0.0",
			  "id": 2,
			  "topology": {
				"components": [],
				"description": "集群拓扑",
				"isDefault": true,
				"name": "cluster"
			  }
			},
			"bkAppAbbr": "",
			"bkAppCode": "",
			"bkBizId": 1,
			"bkBizName": "测试业务",
			"bkBizTitle": "[1]测试业务",
			"clusterAlias": "Test Cluster",
			"clusterName": "test-cluster",
			"createdBy": "admin",
			"description": "just for test",
			"id": 2,
			"k8sClusterConfig": {
			  "active": true,
			  "apiServerUrl": "https://www.example.com",
			  "caCert": "test-ca-cert",
			  "clientCert": "test-client-cert",
			  "clientKey": "test-client-key",
			  "clusterName": "test-k8s-cluster",
			  "createdBy": "admin",
			  "description": "测试K8s集群配置",
			  "id": 2,
			  "isPublic": true,
			  "password": "test-password",
			  "provider": "test-provider",
			  "regionCode": "test-region-code",
			  "regionName": "test-region",
			  "token": "test-token",
			  "updatedBy": "admin",
			  "username": "test-user"
			},
			"namespace": "default",
			"requestId": "",
			"serviceVersion": "",
			"status": "CREATED",
			"tags": [],
			"terminationPolicy": "",
			"topoName": "cluster",
			"topoNameAlias": "",
			"updatedBy": "admin"
		  }
		]
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *ClusterControllerTestSuite) TestGetClusterInfo() {
	t := suite.T()
	createMoreCluster(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/cluster/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"addonClusterVersion": "",
		"addonInfo": {
		  "active": true,
		  "addonCategory": "storage",
		  "addonName": "test-storage-addon",
		  "addonType": "storage",
		  "addonVersion": "1.0.0",
		  "id": 1,
		  "topology": {
			"components": [],
			"description": "集群拓扑",
			"isDefault": true,
			"name": "cluster"
		  }
		},
		"bkAppAbbr": "",
		"bkAppCode": "",
		"bkBizId": 1,
		"bkBizName": "测试业务",
		"bkBizTitle": "[1]测试业务",
		"clusterAlias": "Test Cluster",
		"clusterName": "test-cluster",
		"createdBy": "admin",
		"description": "just for test",
		"id": 1,
		"k8sClusterConfig": {
		  "active": true,
		  "apiServerUrl": "https://www.example.com",
		  "caCert": "test-ca-cert",
		  "clientCert": "test-client-cert",
		  "clientKey": "test-client-key",
		  "clusterName": "test-k8s-cluster",
		  "createdBy": "admin",
		  "description": "测试K8s集群配置",
		  "id": 1,
		  "isPublic": true,
		  "password": "test-password",
		  "provider": "test-provider",
		  "regionCode": "test-region-code",
		  "regionName": "test-region",
		  "token": "test-token",
		  "updatedBy": "admin",
		  "username": "test-user"
		},
		"namespace": "default",
		"requestId": "",
		"serviceVersion": "",
		"status": "CREATED",
		"tags": [],
		"terminationPolicy": "",
		"topoName": "cluster",
		"topoNameAlias": "",
		"updatedBy": "admin"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *ClusterControllerTestSuite) TestGetClusterTopology() {
	t := suite.T()
	createMoreCluster(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/cluster/topology/1", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"addonCategory": "storage",
		"addonName": "test-storage-addon",
		"addonType": "storage",
		"addonVersion": "1.0.0",
		"clusterAlias": "Test Cluster",
		"clusterName": "test-cluster",
		"components": null,
		"description": "just for test",
		"isDefault": false,
		"k8sClusterName": "test-k8s-cluster",
		"namespace": "default",
		"relations": null,
		"status": "CREATED",
		"topoName": "cluster"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
