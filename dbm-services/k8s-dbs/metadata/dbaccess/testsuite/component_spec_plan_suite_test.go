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

var componentSpecPlanSample = &model.ComponentSpecPlanModel{
	AddonSpecPlanID: 1,
	ComponentName:   "mysql",
	CPUCores:        intPtr(4),
	MemoryGb:        intPtr(8),
	DiskSizeGb:      intPtr(100),
	Active:          true,
	Description:     "test component spec plan",
	CreatedBy:       "admin",
	UpdatedBy:       "admin",
}

func intPtr(i int) *int {
	return &i
}

type ComponentSpecPlanDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.ComponentSpecPlanDbAccess
	ctx            context.Context
}

func (suite *ComponentSpecPlanDbAccessTestSuite) SetupSuite() {
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
	suite.dbAccess = dbaccess.GetComponentSpecPlanDbAccess(db)
}

func (suite *ComponentSpecPlanDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentSpecPlanDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbComponentSpecPlan, &model.ComponentSpecPlanModel{})
}

func TestComponentSpecPlanDbAccess(t *testing.T) {
	suite.Run(t, new(ComponentSpecPlanDbAccessTestSuite))
}

func (suite *ComponentSpecPlanDbAccessTestSuite) TestCreateAndFindByID() {
	t := suite.T()
	// Create
	created, err := suite.dbAccess.Create(componentSpecPlanSample)
	assert.NoError(t, err)
	assert.NotZero(t, created.ID)
	assert.Equal(t, componentSpecPlanSample.ComponentName, created.ComponentName)
	assert.Equal(t, *componentSpecPlanSample.CPUCores, *created.CPUCores)

	// FindByID
	found, err := suite.dbAccess.FindByID(created.ID)
	assert.NoError(t, err)
	assert.NotNil(t, found)
	assert.Equal(t, created.ID, found.ID)
	assert.Equal(t, componentSpecPlanSample.AddonSpecPlanID, found.AddonSpecPlanID)
}

func (suite *ComponentSpecPlanDbAccessTestSuite) TestUpdate() {
	t := suite.T()
	created, err := suite.dbAccess.Create(componentSpecPlanSample)
	assert.NoError(t, err)

	// Update
	newCPU := 8
	created.CPUCores = &newCPU
	rows, err := suite.dbAccess.Update(created)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	// Verify
	found, err := suite.dbAccess.FindByID(created.ID)
	assert.NoError(t, err)
	assert.Equal(t, newCPU, *found.CPUCores)
}

func (suite *ComponentSpecPlanDbAccessTestSuite) TestDeleteByID() {
	t := suite.T()
	created, err := suite.dbAccess.Create(componentSpecPlanSample)
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

func (suite *ComponentSpecPlanDbAccessTestSuite) TestFindByParams() {
	t := suite.T()
	created, err := suite.dbAccess.Create(componentSpecPlanSample)
	assert.NoError(t, err)

	// Find by params
	params := &metaentity.ComponentSpecPlanQueryParams{
		AddonSpecPlanID: created.AddonSpecPlanID,
		ComponentName:   created.ComponentName,
	}
	results, err := suite.dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.NotEmpty(t, results)
	assert.Equal(t, created.ID, results[0].ID)
}
