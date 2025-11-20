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
	request2 "k8s-dbs/metadata/vo/request"
	"log"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonCategoryRequest = request2.AddonCategoryRequest{
	CategoryName:  "category_name_01",
	CategoryAlias: "category_alias_01",
	Description:   "description_01",
	BKAuth:        baseBKAuth,
}

type AddonCategoryControllerTestSuite struct {
	suite.Suite
	mySQLContainer          *testhelper.MySQLContainerWrapper
	addonCategoryController *controller.AddonCategoryController
	ctx                     context.Context
	router                  *gin.Engine
}

func (suite *AddonCategoryControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonCategoryDbAccess(db)
	typeDbAccess := dbaccess.NewAddonTypeDbAccess(db)
	addonCategoryProvider := provider.NewAddonCategoryProvider(dbAccess, typeDbAccess)
	addonCategoryController := controller.NewAddonCategoryController(addonCategoryProvider)
	suite.addonCategoryController = addonCategoryController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	{
		routerGroup.POST("/addon_category", suite.addonCategoryController.Create)
	}
	listGroup := r.Group("/metadata")
	{
		listGroup.GET("/addon_categories", suite.addonCategoryController.ListByLimit)
	}
	suite.router = r
}

func (suite *AddonCategoryControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonCategoryControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonCategory, &model.AddonCategoryModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonType, &model.AddonTypeModel{})
}

func TestAddonCategoryController(t *testing.T) {
	suite.Run(t, new(AddonCategoryControllerTestSuite))
}

func (suite *AddonCategoryControllerTestSuite) TestCreate() {
	t := suite.T()
	jsonData, _ := json.Marshal(addonCategoryRequest)
	request, _ := http.NewRequest("POST", "/metadata/addon_category", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": {
		"id": 1,
		"categoryName": "category_name_01",
		"categoryAlias": "category_alias_01",
		"description": "description_01",
        "active": true
	  },
		"message": "success",
		"error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}

func (suite *AddonCategoryControllerTestSuite) TestListByLimit() {
	t := suite.T()
	createMoreAddonCategory(suite.mySQLContainer, 2)
	request, _ := http.NewRequest("GET", "/metadata/addon_categories?size=10", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "result": true,
	  "code": 200,
	  "data": [
		{
		  "id": 1,
		  "categoryName": "category_name_01",
		  "categoryAlias": "category_alias_01",
		  "description": "description_01",
		  "active": true,
          "addonTypes": []
		},
		{
		  "id": 2,
		  "categoryName": "category_name_01",
		  "categoryAlias": "category_alias_01",
		  "description": "description_01",
		  "active": true,
          "addonTypes": []
		}
	  ],
	  "message": "success",
	  "error": null
	}
	`
	assert.JSONEq(t, expected, w.Body.String())
}
