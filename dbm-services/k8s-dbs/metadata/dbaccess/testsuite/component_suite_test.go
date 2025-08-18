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
	"k8s-dbs/metadata/model"
	"log"
	"log/slog"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var componentSample = &model.K8sCrdComponentModel{
	ComponentName: "component-01",
	CrdClusterID:  1,
	Status:        "Enable",
	Description:   "desc",
}

type ComponentDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sCrdComponentDbAccess
	ctx            context.Context
}

func (suite *ComponentDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *ComponentDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdComponent, &model.K8sCrdComponentModel{})
}

func (suite *ComponentDbAccessTestSuite) TestCreateComponent() {
	t := suite.T()
	component, err := suite.dbAccess.Create(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)
	assert.Equal(t, component.ComponentName, componentSample.ComponentName)
	assert.Equal(t, component.CrdClusterID, componentSample.CrdClusterID)
	assert.Equal(t, component.Status, componentSample.Status)
}

func (suite *ComponentDbAccessTestSuite) TestDeleteComponent() {
	t := suite.T()
	component, err := suite.dbAccess.Create(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)

	rows, err := suite.dbAccess.DeleteByID(component.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ComponentDbAccessTestSuite) TestUpdateComponent() {
	t := suite.T()
	component, err := suite.dbAccess.Create(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)

	newComponent := &model.K8sCrdComponentModel{
		ID:            component.ID,
		ComponentName: "component-02",
		CrdClusterID:  2,
		Status:        "Disable",
		Description:   "update success",
	}
	rows, err := suite.dbAccess.Update(newComponent)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ComponentDbAccessTestSuite) TestGetComponent() {
	t := suite.T()
	component, err := suite.dbAccess.Create(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)

	foundComponent, err := suite.dbAccess.FindByID(component.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundComponent)
	slog.Info("Print component", "Component", foundComponent)

	assert.Equal(t, component.ComponentName, foundComponent.ComponentName)
	assert.Equal(t, component.CrdClusterID, foundComponent.CrdClusterID)
	assert.Equal(t, component.Status, foundComponent.Status)
}

func (suite *ComponentDbAccessTestSuite) TestDeleteComponentByClusterID() {
	t := suite.T()
	component, err := suite.dbAccess.Create(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)

	rows, err := suite.dbAccess.DeleteByClusterID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestComponentDbAccessTestSuite(t *testing.T) {
	suite.Run(t, new(ComponentDbAccessTestSuite))
}
