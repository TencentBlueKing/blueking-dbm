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
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/helper/testhelper"
	models "k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonTypeSample = &models.AddonTypeModel{
	CategoryID: 1,
	TypeName:   "mysql",
	TypeAlias:  "MySQL Database",
}

var batchAddonTypeSamples = []*models.AddonTypeModel{
	{
		CategoryID: 1,
		TypeName:   "redis",
		TypeAlias:  "Redis Cache",
	},
	{
		CategoryID: 2,
		TypeName:   "mongodb",
		TypeAlias:  "MongoDB Database",
	},
}

type AddonTypeDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonTypeDbAccess
	ctx            context.Context
}

func (suite *AddonTypeDbAccessTestSuite) SetupSuite() {
	suite.ctx = context.Background()
	mySqlContainer, err := testhelper.NewMySQLContainerWrapper(suite.ctx)
	if err != nil {
		log.Fatal(err)
	}
	suite.mySqlContainer = mySqlContainer
	db, err := testhelper.InitDBConnection(mySqlContainer.ConnStr)
	if err != nil {
		log.Fatal(err)
	}
	suite.dbAccess = dbaccess.NewAddonTypeDbAccess(db)
}

func (suite *AddonTypeDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonTypeDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonType, &models.AddonTypeModel{})
}

func (suite *AddonTypeDbAccessTestSuite) TestCreateAddonType() {
	t := suite.T()
	addonType, err := suite.dbAccess.Create(addonTypeSample)
	assert.NoError(t, err)
	assert.NotZero(t, addonType.ID)
	assert.Equal(t, addonTypeSample.CategoryID, addonType.CategoryID)
	assert.Equal(t, addonTypeSample.TypeName, addonType.TypeName)
	assert.Equal(t, addonTypeSample.TypeAlias, addonType.TypeAlias)
}

func (suite *AddonTypeDbAccessTestSuite) TestGetAddonType() {
	t := suite.T()
	addonType, err := suite.dbAccess.Create(addonTypeSample)
	assert.NoError(t, err)
	assert.NotZero(t, addonType.ID)

	foundAddonType, err := suite.dbAccess.FindByID(addonType.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundAddonType)
	assert.Equal(t, addonType.ID, foundAddonType.ID)
	assert.Equal(t, addonType.CategoryID, foundAddonType.CategoryID)
	assert.Equal(t, addonType.TypeName, foundAddonType.TypeName)
	assert.Equal(t, addonType.TypeAlias, foundAddonType.TypeAlias)
}

func (suite *AddonTypeDbAccessTestSuite) TestFindAddonTypeByCategoryID() {
	t := suite.T()
	for _, sample := range batchAddonTypeSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	addonTypes, err := suite.dbAccess.FindByCategoryID(1)
	assert.NoError(t, err)
	assert.NotEmpty(t, addonTypes)
	assert.Len(t, addonTypes, 1)
	assert.Equal(t, batchAddonTypeSamples[0].CategoryID, addonTypes[0].CategoryID)
	assert.Equal(t, batchAddonTypeSamples[0].TypeName, addonTypes[0].TypeName)
	assert.Equal(t, batchAddonTypeSamples[0].TypeAlias, addonTypes[0].TypeAlias)
}

func (suite *AddonTypeDbAccessTestSuite) TestListAddonTypeByLimit() {
	t := suite.T()
	for _, sample := range batchAddonTypeSamples {
		_, err := suite.dbAccess.Create(sample)
		assert.NoError(t, err)
	}

	addonTypes, err := suite.dbAccess.ListByLimit(10)
	assert.NoError(t, err)
	assert.Equal(t, len(batchAddonTypeSamples), len(addonTypes))

	typeMap := make(map[string]*models.AddonTypeModel)
	for _, addonType := range addonTypes {
		typeMap[addonType.TypeName] = addonType
	}

	for _, sample := range batchAddonTypeSamples {
		foundType, ok := typeMap[sample.TypeName]
		assert.True(t, ok, "AddonType with name %s not found", sample.TypeName)
		assert.Equal(t, sample.CategoryID, foundType.CategoryID)
		assert.Equal(t, sample.TypeAlias, foundType.TypeAlias)
	}
}

func TestAddonTypeDbAccessTestSuite(t *testing.T) {
	suite.Run(t, new(AddonTypeDbAccessTestSuite))
}
