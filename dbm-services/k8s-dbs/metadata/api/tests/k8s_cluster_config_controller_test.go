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
	"bytes"
	"encoding/json"
	"fmt"
	"k8s-dbs/metadata/api/controller"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/req"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func initConfigTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_cluster_config;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_cluster_config table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sClusterConfigModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_cluster_config table")
		return nil, err
	}
	return db, nil
}

func AddSampleConfig() error {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return err
	}
	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	config := &model.K8sClusterConfigModel{
		ClusterName:  "BCS-K8S-000",
		APIServerURL: "https://127.0.0.1:60002",
		CACert:       "test_ca_cert",
		ClientCert:   "test_client_cert",
		ClientKey:    "test_client_key",
		Token:        "test_token",
		Username:     "test_username",
		Password:     "test_password",
		Description:  "just for test",
		CreatedBy:    "admin",
		UpdatedBy:    "admin",
	}
	added, _ := dbAccess.Create(config)
	fmt.Printf("Created config %+v\n", added)
	return nil
}

func SetupConfigRouter() *gin.Engine {
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	db, _ := initConfigTable()
	configDbaccess := dbaccess.NewK8sClusterConfigDbAccess(db)
	configProvider := provider.NewK8sClusterConfigProvider(configDbaccess)
	configController := controller.NewK8sClusterConfigController(configProvider)
	{
		routerGroup.GET("/k8s_cluster_config/id/:id", configController.GetK8sClusterConfigByID)
		routerGroup.GET("/k8s_cluster_config/name/:cluster_name", configController.GetK8sClusterConfigByName)
		routerGroup.DELETE("/k8s_cluster_config/:id", configController.DeleteK8sClusterConfig)
		routerGroup.POST("/k8s_cluster_config", configController.CreateK8sClusterConfig)
		routerGroup.PUT("/k8s_cluster_config/:id", configController.UpdateK8sClusterConfig)
	}
	return r
}

func TestCreateConfig(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupConfigRouter()

	reqVo := req.K8sClusterConfigReqVo{
		ClusterName:  "BCS-K8S-000",
		APIServerURL: "https://127.0.0.1:60002",
		CACert:       "test_ca_cert",
		ClientCert:   "test_client_cert",
		ClientKey:    "test_client_key",
		Token:        "test_token",
		Username:     "test_username",
		Password:     "test_password",
		Description:  "just for test",
		CreatedBy:    "admin",
		UpdatedBy:    "admin",
	}

	requestBody, err := json.Marshal(&reqVo)
	assert.NoError(t, err)

	request, err := http.NewRequest("POST", "/metadata/k8s_cluster_config", bytes.NewBuffer(requestBody))
	assert.NoError(t, err)
	request.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)

	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"clusterName":  "BCS-K8S-000",
			"apiServerUrl": "https://127.0.0.1:60002",
			"caCert":       "test_ca_cert",
			"clientCert":   "test_client_cert",
			"clientKey":    "test_client_key",
			"token":        "test_token",
			"active": 		true,
			"username":     "test_username",
			"password":     "test_password",
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

func TestGetConfigById(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupConfigRouter()
	err := AddSampleConfig()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/k8s_cluster_config/id/1", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"clusterName":  "BCS-K8S-000",
			"apiServerUrl": "https://127.0.0.1:60002",
			"caCert":       "test_ca_cert",
			"clientCert":   "test_client_cert",
			"clientKey":    "test_client_key",
			"token":        "test_token",
			"username":     "test_username",
			"password":     "test_password",
			"active": 		true,
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

func TestGetConfigByName(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupConfigRouter()
	err := AddSampleConfig()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/k8s_cluster_config/name/BCS-K8S-000", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"clusterName":  "BCS-K8S-000",
			"apiServerUrl": "https://127.0.0.1:60002",
			"caCert":       "test_ca_cert",
			"clientCert":   "test_client_cert",
			"clientKey":    "test_client_key",
			"token":        "test_token",
			"username":     "test_username",
			"password":     "test_password",
			"active": 		true,
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

func TestDeleteConfig(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupConfigRouter()
	err := AddSampleConfig()
	assert.NoError(t, err)
	request, _ := http.NewRequest("DELETE", "/metadata/k8s_cluster_config/1", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)

	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"rows":1
		},
		"message": "OK",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func TestUpdateConfig(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupConfigRouter()
	err := AddSampleConfig()
	assert.NoError(t, err)
	configReq := req.K8sClusterConfigReqVo{
		ClusterName:  "BCS-K8S-001",
		APIServerURL: "https://127.0.0.1:60001",
		CACert:       "test_ca_cert1",
		ClientCert:   "test_client_cert1",
		ClientKey:    "test_client_key1",
		Token:        "test_token1",
		Username:     "test_username1",
		Password:     "test_password1",
		Description:  "just for test2",
		CreatedBy:    "admin2",
		UpdatedBy:    "admin2",
	}

	requestBody, err := json.Marshal(&configReq)
	assert.NoError(t, err)

	request, err := http.NewRequest("PUT", "/metadata/k8s_cluster_config/1", bytes.NewBuffer(requestBody))
	assert.NoError(t, err)
	request.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)

	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"rows":1
		},
		"message": "OK",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}
