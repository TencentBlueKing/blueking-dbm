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
	entitys "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"log/slog"
	"testing"

	"github.com/stretchr/testify/suite"

	"github.com/stretchr/testify/assert"
)

var componentSample = &entitys.K8sCrdComponentEntity{
	ComponentName: "component-01",
	CrdClusterID:  1,
	Status:        "Enable",
	Description:   "desc",
}

type ComponentProviderTestSuite struct {
	suite.Suite
	mySqlContainer    *testhelper.MySQLContainerWrapper
	componentProvider provider.K8sCrdComponentProvider
	ctx               context.Context
}

func (suite *ComponentProviderTestSuite) SetupSuite() {
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
	componentProvider := provider.NewK8sCrdComponentProvider(dbAccess)
	suite.componentProvider = componentProvider
}

func (suite *ComponentProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ComponentProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sCrdComponent, &model.K8sCrdComponentModel{})
}

func TestComponentProviderTestSuite(t *testing.T) {
	suite.Run(t, new(ComponentProviderTestSuite))
}

func (suite *ComponentProviderTestSuite) TestCreateComponent() {
	t := suite.T()
	component, err := suite.componentProvider.CreateComponent(componentSample)
	assert.NoError(t, err)
	assert.NotNil(t, component.ID)
	assert.Equal(t, componentSample.ComponentName, component.ComponentName)
	assert.Equal(t, componentSample.CrdClusterID, component.CrdClusterID)
	assert.Equal(t, componentSample.Status, component.Status)
	assert.Equal(t, componentSample.Description, component.Description)
}

func (suite *ComponentProviderTestSuite) TestDeleteComponent() {
	t := suite.T()
	component, err := suite.componentProvider.CreateComponent(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)

	rows, err := suite.componentProvider.DeleteComponentByID(component.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ComponentProviderTestSuite) TestUpdateComponent() {
	t := suite.T()
	component, err := suite.componentProvider.CreateComponent(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)

	newEntity := &entitys.K8sCrdComponentEntity{
		ID:            component.ID,
		ComponentName: "component-02",
		CrdClusterID:  2,
		Status:        "Disable",
		Description:   "update success",
	}
	rows, err := suite.componentProvider.UpdateComponent(newEntity)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ComponentProviderTestSuite) TestGetComponent() {
	t := suite.T()
	component, err := suite.componentProvider.CreateComponent(componentSample)
	assert.NoError(t, err)
	assert.NotZero(t, component.ID)

	foundComponent, err := suite.componentProvider.FindComponentByID(component.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundComponent)
	slog.Info("Print component", "Component", foundComponent)

	assert.Equal(t, component.ComponentName, foundComponent.ComponentName)
	assert.Equal(t, component.CrdClusterID, foundComponent.CrdClusterID)
	assert.Equal(t, component.Status, foundComponent.Status)
}
