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
	"k8s-dbs/metadata/api/vo/req"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/dbaccess/model"
	"k8s-dbs/metadata/provider"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func initComponentTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_component;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_component table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_component table")
		return nil, err
	}
	return db, nil
}

func AddSampleComponent() error {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return err
	}
	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)

	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, _ := time.Parse(layout, addDateTime)

	component := &model.K8sCrdComponentModel{
		ComponentName: "test1",
		CrdClusterID:  1,
		Status:        "CREATED",
		Description:   "just for test",
		CreatedBy:     "admin",
		CreatedAt:     parsedTime,
		UpdatedAt:     parsedTime,
		UpdatedBy:     "admin",
	}
	addedComponent, err := dbAccess.Create(component)
	fmt.Printf("Created component %+v\n", addedComponent)
	return nil
}

func SetupComponentRouter() *gin.Engine {
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	db, _ := initComponentTable()
	componentDbaccess := dbaccess.NewK8sCrdComponentAccess(db)
	componentProvider := provider.NewK8sCrdComponentProvider(componentDbaccess)
	componentController := controller.NewComponentController(componentProvider)
	{
		routerGroup.GET("/component/:id", componentController.GetComponent)
	}
	return r
}

func TestCreateComponent(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupComponentRouter()
	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	componentRequest := req.K8sCrdComponentReqVo{
		ComponentName: "test1",
		CrdClusterID:  1,
		Description:   "just for test",
		CreatedBy:     "admin",
		CreatedAt:     parsedTime,
		UpdatedAt:     parsedTime,
		UpdatedBy:     "admin",
	}

	requestBody, err := json.Marshal(&componentRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("POST", "/metadata/component", bytes.NewBuffer(requestBody))
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
			"crd_cluster_id": 1,
			"component_name": "test1",
			"metadata": "{\"namespace\":\"default\"}",
			"spec": "{\"replicas\":1}",
			"status": "CREATED",
			"description": "just for test",
			"created_by": "admin",
			"created_at": "2025-01-01T20:00:00+08:00",
			"updated_by": "admin",
			"updated_at": "2025-01-01T20:00:00+08:00"
		},
		"message": "OK",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func TestGetComponent(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupComponentRouter()
	err := AddSampleComponent()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/component/1", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"crd_cluster_id": 1,
			"component_name": "test1",
			"metadata": "{\"namespace\":\"default\"}",
			"spec": "{\"replicas\":1}",
			"status": "CREATED",
			"description": "just for test",
			"created_by": "admin",
			"created_at": "2025-01-01T20:00:00+08:00",
			"updated_by": "admin",
			"updated_at": "2025-01-01T20:00:00+08:00"
		},
		"message": "OK",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func TestDeleteComponent(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupComponentRouter()
	err := AddSampleComponent()
	assert.NoError(t, err)
	request, _ := http.NewRequest("DELETE", "/metadata/component/1", nil)
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

func TestUpdateComponent(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupComponentRouter()
	err := AddSampleComponent()
	assert.NoError(t, err)
	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	componentRequest := req.K8sCrdComponentReqVo{
		ComponentName: "test2",
		CrdClusterID:  2,
		Description:   "just for test2",
		CreatedBy:     "admin2",
		CreatedAt:     parsedTime,
		UpdatedAt:     parsedTime,
		UpdatedBy:     "admin2",
	}

	requestBody, err := json.Marshal(&componentRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("PUT", "/metadata/component/1", bytes.NewBuffer(requestBody))
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
