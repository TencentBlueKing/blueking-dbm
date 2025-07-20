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

package tests

import (
	"fmt"
	"k8s-dbs/metadata/api/controller"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func initClusterTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_cluster;").Error; err != nil {
		fmt.Println("Failed to drop k8s_crd_clusters table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdClusterModel{}); err != nil {
		fmt.Println("Failed to migrate k8s_crd_clusters table")
		return nil, err
	}
	return db, nil
}

func AddSampleCluster() error {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return err
	}
	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "test1",
		AddonID:            1,
		RequestID:          "1",
		K8sClusterConfigID: 1,
		Status:             "CREATED",
		Description:        "just for test",
		CreatedBy:          "admin",
		UpdatedBy:          "admin",
	}
	addedCluster, err := dbAccess.Create(cluster)
	fmt.Printf("Created cluster %+v\n", addedCluster)
	return nil
}

func SetupClusterRouter() *gin.Engine {
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	db, _ := initClusterTable()
	clusterDbaccess := dbaccess.NewCrdClusterDbAccess(db)
	addonDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := dbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)
	clusterTopologyDbAccess := dbaccess.NewAddonTopologyDbAccess(db)

	clusterProviderBuilder := provider.K8sCrdClusterProviderBuilder{}
	clusterProvider, err := provider.NewK8sCrdClusterProvider(
		clusterProviderBuilder.WithClusterDbAccess(clusterDbaccess),
		clusterProviderBuilder.WithAddonDbAccess(addonDbAccess),
		clusterProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
	)
	if err != nil {
		panic(err)
	}
	clusterController := controller.NewClusterController(clusterProvider)
	{
		routerGroup.GET("/cluster/:id", clusterController.GetClusterInfo)
	}
	return r
}

func TestGetCluster(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupClusterRouter()
	err := AddSampleCluster()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/cluster/1", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"addonId": 1,
			"k8sClusterConfigId": 1,
			"clusterName": "test1",
			"requestId": "1",
			"status": "CREATED",
			"description": "just for test",
			"createdBy": "admin",
			"createdAt": "2025-01-01T20:00:00+08:00",
			"updatedBy": "admin",
			"updatedAt": "2025-01-01T20:00:00+08:00"
		},
		"message": "OK",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}
