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

func initCmpdTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_componentdefinition;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_componentdefinition table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentDefinitionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_componentdefinition table")
		return nil, err
	}
	return db, nil
}

func AddSampleCmpd() error {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return err
	}
	dbAccess := dbaccess.NewK8sCrdCmpdDbAccess(db)

	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, _ := time.Parse(layout, addDateTime)

	cmpd := &model.K8sCrdComponentDefinitionModel{
		AddonID:                 1,
		ComponentDefinitionName: "surrealdb",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":1}",
		Active:                  true,
		Description:             "just for test",
		CreatedBy:               "admin",
		CreatedAt:               parsedTime,
		UpdatedAt:               parsedTime,
		UpdatedBy:               "admin",
	}
	added, _ := dbAccess.Create(cmpd)
	fmt.Printf("Created cmpd %+v\n", added)
	return nil
}

func SetupCmpdRouter() *gin.Engine {
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	db, _ := initCmpdTable()
	cmpdDbaccess := dbaccess.NewK8sCrdCmpdDbAccess(db)
	cmpdProvider := provider.NewK8sCrdCmpdProvider(cmpdDbaccess)
	cmpdController := controller.NewCmpdController(cmpdProvider)
	{
		routerGroup.GET("/cmpd/:id", cmpdController.GetCmpd)
		routerGroup.DELETE("/cmpd/:id", cmpdController.DeleteCmpd)
		routerGroup.POST("/cmpd", cmpdController.CreateCmpd)
		routerGroup.PUT("/cmpd/:id", cmpdController.UpdateCmpd)
	}
	return r
}

func TestCreateCmpd(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpdRouter()
	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	cmpdRequest := req.K8sCrdCmpdReqVo{
		AddonID:                 1,
		ComponentDefinitionName: "surrealdb",
		Metadata:                "{\"namespace\":\"default\"}",
		Spec:                    "{\"replicas\":1}",
		Description:             "just for test",
		CreatedBy:               "admin",
		CreatedAt:               parsedTime,
		UpdatedAt:               parsedTime,
		UpdatedBy:               "admin",
	}

	requestBody, err := json.Marshal(&cmpdRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("POST", "/metadata/cmpd", bytes.NewBuffer(requestBody))
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
			"addonId": 1,
			"cmpdName": "surrealdb",
			"metadata": "{\"namespace\":\"default\"}",
			"defaultVersion":"",
			"spec": "{\"replicas\":1}",
			"active": true,
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

func TestGetCmpd(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpdRouter()
	err := AddSampleCmpd()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/cmpd/1", nil)
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
			"cmpdName": "surrealdb",
			"metadata": "{\"namespace\":\"default\"}",
			"defaultVersion":"",
			"spec": "{\"replicas\":1}",
			"active": true,
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

func TestDeleteCmpd(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpdRouter()
	err := AddSampleCmpd()
	assert.NoError(t, err)
	request, _ := http.NewRequest("DELETE", "/metadata/cmpd/1", nil)
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

func TestUpdateCmpd(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupCmpdRouter()
	err := AddSampleCmpd()
	assert.NoError(t, err)
	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	cmpdRequest := req.K8sCrdCmpdReqVo{
		AddonID:                 1,
		ComponentDefinitionName: "surrealdb2",
		Metadata:                "{\"namespace\":\"default2\"}",
		Spec:                    "{\"replicas\":2}",
		Description:             "just for test2",
		CreatedBy:               "admin2",
		CreatedAt:               parsedTime,
		UpdatedAt:               parsedTime,
		UpdatedBy:               "admin2",
	}

	requestBody, err := json.Marshal(&cmpdRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("PUT", "/metadata/cmpd/1", bytes.NewBuffer(requestBody))
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
