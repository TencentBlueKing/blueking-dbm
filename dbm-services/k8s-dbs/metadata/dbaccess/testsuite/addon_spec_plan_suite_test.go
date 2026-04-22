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
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var addonSpecPlanSample = &model.AddonSpecPlanModel{
	AddonID:        1,
	AddonTopology:  "standalone",
	SpecLevel:      "basic",
	SpecLevelAlias: "基础版",
	Active:         true,
	Description:    "test addon spec plan",
	CreatedBy:      "admin",
	UpdatedBy:      "admin",
}

type AddonSpecPlanDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.AddonSpecPlanDbAccess
	ctx            context.Context
}

func (suite *AddonSpecPlanDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbaccess.GetAddonSpecPlanDbAccess(db)
}

func (suite *AddonSpecPlanDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *AddonSpecPlanDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbAddonSpecPlan, &model.AddonSpecPlanModel{})
}

func TestAddonSpecPlanDbAccess(t *testing.T) {
	suite.Run(t, new(AddonSpecPlanDbAccessTestSuite))
}

func (suite *AddonSpecPlanDbAccessTestSuite) TestCreateAndFindByID() {
	t := suite.T()
	// Create
	created, err := suite.dbAccess.Create(addonSpecPlanSample)
	assert.NoError(t, err)
	assert.NotZero(t, created.ID)
	assert.Equal(t, addonSpecPlanSample.AddonID, created.AddonID)
	assert.Equal(t, addonSpecPlanSample.SpecLevel, created.SpecLevel)

	// FindByID
	found, err := suite.dbAccess.FindByID(created.ID)
	assert.NoError(t, err)
	assert.NotNil(t, found)
	assert.Equal(t, created.ID, found.ID)
	assert.Equal(t, addonSpecPlanSample.AddonTopology, found.AddonTopology)
}

func (suite *AddonSpecPlanDbAccessTestSuite) TestUpdate() {
	t := suite.T()
	created, err := suite.dbAccess.Create(addonSpecPlanSample)
	assert.NoError(t, err)

	// Update
	newLevel := "premium"
	created.SpecLevel = newLevel
	rows, err := suite.dbAccess.Update(created)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	// Verify
	found, err := suite.dbAccess.FindByID(created.ID)
	assert.NoError(t, err)
	assert.Equal(t, newLevel, found.SpecLevel)
}

func (suite *AddonSpecPlanDbAccessTestSuite) TestDeleteByID() {
	t := suite.T()
	created, err := suite.dbAccess.Create(addonSpecPlanSample)
	assert.NoError(t, err)

	// Delete
	rows, err := suite.dbAccess.DeleteByID(created.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	// Verify deleted
	found, err := suite.dbAccess.FindByID(created.ID)
	assert.Error(t, err)
	assert.Nil(t, found)
}

func (suite *AddonSpecPlanDbAccessTestSuite) TestFindByParams() {
	t := suite.T()
	created, err := suite.dbAccess.Create(addonSpecPlanSample)
	assert.NoError(t, err)

	// Find by params
	params := &metaentity.AddonSpecPlanQueryParams{
		AddonID:   created.AddonID,
		SpecLevel: created.SpecLevel,
	}
	results, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.NotEmpty(t, results)
	assert.Equal(t, created.ID, results[0].ID)
}
