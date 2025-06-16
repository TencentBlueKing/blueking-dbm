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

func initAddonTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_storageaddon;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_storageaddon table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdStorageAddonModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_storageaddon table")
		return nil, err
	}
	return db, nil
}

func AddSampleAddon() error {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return err
	}
	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, _ := time.Parse(layout, addDateTime)

	addon := &model.K8sCrdStorageAddonModel{
		AddonName:     "surrealdb-2.2.0",
		AddonCategory: "Graph",
		AddonType:     "SurrealDB",
		AddonVersion:  "2.2.0",
		Active:        true,
		Description:   "just for test",
		CreatedBy:     "admin",
		CreatedAt:     parsedTime,
		UpdatedAt:     parsedTime,
		UpdatedBy:     "admin",
	}
	added, _ := dbAccess.Create(addon)
	fmt.Printf("Created addon %+v\n", added)
	return nil
}

func AddSampleAddons() error {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return err
	}
	dbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)

	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, _ := time.Parse(layout, addDateTime)

	addons := []model.K8sCrdStorageAddonModel{
		{
			AddonName:     "surreal",
			AddonCategory: "Graph",
			AddonType:     "SurrealDB",
			AddonVersion:  "2.2.0",
			Active:        true,
			Description:   "just for test",
			CreatedBy:     "admin",
			CreatedAt:     parsedTime,
			UpdatedAt:     parsedTime,
			UpdatedBy:     "admin",
		},
		{
			AddonName:     "vm",
			AddonCategory: "Time-Series",
			AddonType:     "VictoriaMetric",
			AddonVersion:  "2.2.0",
			Active:        true,
			Description:   "just for test",
			CreatedBy:     "admin",
			CreatedAt:     parsedTime,
			UpdatedAt:     parsedTime,
			UpdatedBy:     "admin",
		},
	}
	for _, addon := range addons {
		_, _ = dbAccess.Create(&addon)
	}
	return nil
}

func SetupAddonRouter() *gin.Engine {
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	db, _ := initAddonTable()
	addonDbaccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	addonProvider := provider.NewK8sCrdStorageAddonProvider(addonDbaccess)
	addonController := controller.NewAddonController(addonProvider)
	{
		routerGroup.GET("/addon", addonController.ListAddons)
		routerGroup.GET("/addon/:id", addonController.GetAddon)
		routerGroup.DELETE("/addon/:id", addonController.DeleteAddon)
		routerGroup.POST("/addon", addonController.CreateAddon)
		routerGroup.PUT("/addon/:id", addonController.UpdateAddon)
	}
	return r
}

func TestCreateAddon(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupAddonRouter()

	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	addonRequest := req.K8sCrdAddonReqVo{
		AddonName:            "surrealdb-2.2.0",
		AddonCategory:        "Graph",
		AddonType:            "SurrealDB",
		AddonVersion:         "2.2.0",
		RecommendedVersion:   "1.0.0",
		SupportedVersions:    "[\"1.0.0\"]",
		RecommendedAcVersion: "1.0.0",
		SupportedAcVersions:  "[\"1.0.0\"]",
		Topologies:           "{}",
		Releases:             "{}",
		Description:          "just for test",
		CreatedBy:            "admin",
		CreatedAt:            parsedTime,
		UpdatedAt:            parsedTime,
		UpdatedBy:            "admin",
	}

	requestBody, err := json.Marshal(&addonRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("POST", "/metadata/addon", bytes.NewBuffer(requestBody))
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
			"addonName": "surrealdb-2.2.0",
            "addonType": "SurrealDB",
			"addonCategory": "Graph",
			"addonVersion": "2.2.0",
			"recommendedVersion":   "1.0.0",
			"supportedVersions":    "[\"1.0.0\"]",
			"recommendedAcVersion": "1.0.0",
			"supportedAcVersions":  "[\"1.0.0\"]",
			"topologies":           "{}",
			"releases":             "{}",
			"active": true,
			"description": "just for test",
			"createdBy": "admin",
			"createdAt": "2025-01-01T12:00:00Z",
			"updatedBy": "admin",
			"updatedAt": "2025-01-01T12:00:00Z"
		},
		"message": "OK",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func TestGetAddon(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupAddonRouter()
	err := AddSampleAddon()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/addon/1", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": {
			"id": 1,
			"addonName": "surrealdb-2.2.0",
            "addonType": "SurrealDB",
			"addonCategory": "Graph",
			"addonVersion": "2.2.0",
			"recommendedVersion":   "",
			"supportedVersions":    "",
			"recommendedAcVersion": "",
			"supportedAcVersions":  "",
			"topologies":           "",
			"releases":             "",
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

func TestDeleteAddon(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupAddonRouter()
	err := AddSampleAddon()
	assert.NoError(t, err)
	request, _ := http.NewRequest("DELETE", "/metadata/addon/1", nil)
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

func TestUpdateAddon(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupAddonRouter()
	err := AddSampleAddon()
	assert.NoError(t, err)
	// 解析时间字符串为 time.Time 对象
	addDateTime := "2025-01-01 12:00:00"
	layout := "2006-01-02 15:04:05"
	parsedTime, err := time.Parse(layout, addDateTime)
	assert.NoError(t, err)

	addonRequest := req.K8sCrdAddonReqVo{
		AddonName:            "surrealdb-2.2.2",
		AddonType:            "SurrealDB-2",
		AddonCategory:        "Graph-2",
		AddonVersion:         "2.2.0",
		RecommendedVersion:   "1.0.0",
		SupportedVersions:    "[\"1.0.0\"]",
		RecommendedAcVersion: "1.0.0",
		SupportedAcVersions:  "[\"1.0.0\"]",
		Topologies:           "{}",
		Releases:             "{}",
		Description:          "just for test2",
		CreatedBy:            "admin2",
		CreatedAt:            parsedTime,
		UpdatedAt:            parsedTime,
		UpdatedBy:            "admin2",
	}

	requestBody, err := json.Marshal(&addonRequest)
	assert.NoError(t, err)

	request, err := http.NewRequest("PUT", "/metadata/addon/1", bytes.NewBuffer(requestBody))
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

func TestListAddons(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupAddonRouter()
	err := AddSampleAddons()
	assert.NoError(t, err)
	request, _ := http.NewRequest("GET", "/metadata/addon?size=10", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
		"result": true,
		"code": 200,
		"data": [
			{
				"id": 1,
				"addonName": "surreal",
				"addonType": "SurrealDB",
				"addonCategory": "Graph",
				"addonVersion": "2.2.0",
				"recommendedVersion":   "",
				"supportedVersions":    "",
				"recommendedAcVersion": "",
				"supportedAcVersions":  "",
				"topologies":           "",
				"releases":             "",
				"active": true,
				"description": "just for test",
				"createdBy": "admin",
				"createdAt": "2025-01-01T20:00:00+08:00",
				"updatedBy": "admin",
				"updatedAt": "2025-01-01T20:00:00+08:00"
			},
			{
				"id": 2,
				"addonName": "vm",
				"addonType": "VictoriaMetric",
				"addonCategory": "Time-Series",
				"addonVersion": "2.2.0",
				"recommendedVersion":   "",
				"supportedVersions":    "",
				"recommendedAcVersion": "",
				"supportedAcVersions":  "",
				"topologies":           "",
				"releases":             "",
				"active": true,
				"description": "just for test",
				"createdBy": "admin",
				"createdAt": "2025-01-01T20:00:00+08:00",
				"updatedBy": "admin",
				"updatedAt": "2025-01-01T20:00:00+08:00"
			}
		],
		"message": "OK",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}
