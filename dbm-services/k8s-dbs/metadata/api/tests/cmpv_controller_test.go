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

func initCmpvTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open("root:123456@tcp(127.0.0.1:3306)/bkbase_dbs?charset=utf8mb4&parseTime=True&loc=Local"), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_componentversion;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_componentversion table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentVersionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_componentversion table")
		return nil, err
	}
	return db, nil
}

func AddSampleCmpv() error {
	db, err := gorm.Open(mysql.Open("root:123456@tcp(127.0.0.1:3306)/bkbase_dbs?charset=utf8mb4&parseTime=True&loc=Local"), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return err
	}
	dbAccess := dbaccess.NewK8sCrdCmpvDbAccess(db)

	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, _ := time.Parse(layout, addDateTime)

	cmpv := &model.K8sCrdComponentVersionModel{
		AddonID:              1,
		ComponentVersionName: "surrealdb",
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":1}",
		Active:               true,
		Description:          "just for test",
		CreatedBy:            "admin",
		CreatedAt:            parsedTime,
		UpdatedAt:            parsedTime,
		UpdatedBy:            "admin",
	}
	added, _ := dbAccess.Create(cmpv)
	fmt.Printf("Created cmpv %+v\n", added)
	return nil
}

func SetupCmpvRouter() *gin.Engine {
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	db, _ := initCmpvTable()
	cmpvDbaccess := dbaccess.NewK8sCrdCmpvDbAccess(db)
	cmpvProvider := provider.NewK8sCrdCmpvProvider(cmpvDbaccess)
	cmpvController := controller.NewCmpvController(cmpvProvider)
	{
		routerGroup.GET("/cmpv/:id", cmpvController.GetCmpv)
		routerGroup.DELETE("/cmpv/:id", cmpvController.DeleteCmpv)
		routerGroup.POST("/cmpv", cmpvController.CreateCmpv)
		routerGroup.PUT("/cmpv/:id", cmpvController.UpdateCmpv)
	}
	return r
}

func TestCreateCmpv(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpvRouter()
	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	cmpvRequest := req.K8sCrdCmpvReqVo{
		AddonID:              1,
		ComponentVersionName: "surrealdb",
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":1}",
		Description:          "just for test",
		CreatedBy:            "admin",
		CreatedAt:            parsedTime,
		UpdatedAt:            parsedTime,
		UpdatedBy:            "admin",
	}

	requestBody, err := json.Marshal(&cmpvRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("POST", "/metadata/cmpv", bytes.NewBuffer(requestBody))
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
			"addon_id": 1,
			"componentversion_name": "surrealdb",
			"metadata": "{\"namespace\":\"default\"}",
			"spec": "{\"replicas\":1}",
			"active": true,
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

func TestGetCmpv(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpvRouter()
	err := AddSampleCmpv()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/cmpv/1", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"addon_id": 1,
			"componentversion_name": "surrealdb",
			"metadata": "{\"namespace\":\"default\"}",
			"spec": "{\"replicas\":1}",
			"active": true,
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

func TestDeleteCmpv(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpvRouter()
	err := AddSampleCmpv()
	assert.NoError(t, err)
	request, _ := http.NewRequest("DELETE", "/metadata/cmpv/1", nil)
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

func TestUpdateCmpv(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpvRouter()
	err := AddSampleCmpv()
	assert.NoError(t, err)
	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	cmpvRequest := req.K8sCrdCmpvReqVo{
		AddonID:              1,
		ComponentVersionName: "surrealdb2",
		Metadata:             "{\"namespace\":\"default2\"}",
		Spec:                 "{\"replicas\":2}",
		Description:          "just for test2",
		CreatedBy:            "admin2",
		CreatedAt:            parsedTime,
		UpdatedAt:            parsedTime,
		UpdatedBy:            "admin2",
	}

	requestBody, err := json.Marshal(&cmpvRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("PUT", "/metadata/cmpv/1", bytes.NewBuffer(requestBody))
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
