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

var addonTypeRequest = vo.AddonTypeRequest{
	CategoryID:  uint64(1),
	TypeName:    "addon_type_name_01",
	TypeAlias:   "addon_type_alias_01",
	Description: "addon_type_description_01",
	BKAuth:      baseBKAuth,
}

type AddonTypeControllerTestSuite struct {
	suite.Suite
	mySQLContainer      *testhelper.MySQLContainerWrapper
	addonTypeController *controller.AddonTypeController
	ctx                 context.Context
	router              *gin.Engine
}

func (suite *AddonTypeControllerTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewAddonTypeDbAccess(db)
	categoryDbAccess := dbaccess.NewAddonCategoryDbAccess(db)
	addonProvider := provider.NewAddonTypeProvider(dbAccess, categoryDbAccess)
	addonTypeController := controller.NewAddonTypeController(addonProvider)
	suite.addonTypeController = addonTypeController
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	routerGroup := r.Group("/metadata")
	{
		routerGroup.POST("/addon_type", suite.addonTypeController.Create)
		routerGroup.GET("/addon_types", suite.addonTypeController.ListByLimit)
	}
	suite.router = r
}

func (suite *AddonTypeControllerTestSuite) TearDownSuite() {
	if err := suite.mySQLContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonTypeControllerTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonType, &model.AddonTypeModel{})
	testhelper.InitTestTable(suite.mySQLContainer.ConnStr, constant.TbAddonCategory, &model.AddonCategoryModel{})
}

func TestAddonTypeController(t *testing.T) {
	suite.Run(t, new(AddonTypeControllerTestSuite))
}

func (suite *AddonTypeControllerTestSuite) TestCreate() {
	t := suite.T()
	jsonData, _ := json.Marshal(addonTypeRequest)
	request, _ := http.NewRequest("POST", "/metadata/addon_type", bytes.NewReader(jsonData))
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": {
		"active": true,
		"addonCategory": null,
		"description": "addon_type_description_01",
		"id": 1,
		"typeAlias": "addon_type_alias_01",
		"typeName": "addon_type_name_01"
	  },
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}

func (suite *AddonTypeControllerTestSuite) TestListByLimit() {
	t := suite.T()
	createMoreAddonCategory(suite.mySQLContainer, 1)
	createMoreAddonType(suite.mySQLContainer, 1)
	request, _ := http.NewRequest("GET", "/metadata/addon_types?size=10", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, request)
	assert.Equal(t, http.StatusOK, w.Code)
	expected := `
	{
	  "code": 200,
	  "data": [
		{
		  "active": true,
		  "addonCategory": {
			"active": true,
			"categoryAlias": "category_alias_01",
			"categoryName": "category_name_01",
			"description": "description_01",
			"id": 1
		  },
		  "description": "addon_type_description_01",
		  "id": 1,
		  "typeAlias": "addon_type_alias_01",
		  "typeName": "addon_type_name_01"
		}
	  ],
	  "error": null,
	  "message": "success",
	  "result": true
	}
	`
	assert.JSONEq(t, expected, deleteTimeColumn(w.Body.Bytes()))
}
