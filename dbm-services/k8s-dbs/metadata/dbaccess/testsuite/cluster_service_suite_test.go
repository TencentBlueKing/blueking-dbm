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
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var clusterServiceSample = &model.K8sClusterServiceModel{
	CrdClusterID:  1,
	ComponentName: "mysql-component",
	ServiceName:   "mysql-service",
	ServiceType:   "ClusterIP",
	Annotations:   "annotation1=value1",
	InternalAddrs: "test.internal",
	ExternalAddrs: "test.external",
	Domains:       "www.example.com",
	Description:   "MySQL service",
}

type ClusterServiceDbAccessTestSuite struct {
	suite.Suite
	mySqlContainer *testhelper.MySQLContainerWrapper
	dbAccess       dbaccess.K8sClusterServiceDbAccess
	ctx            context.Context
}

func (suite *ClusterServiceDbAccessTestSuite) SetupSuite() {
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
	dbAccess := dbaccess.GetClusterServiceDbAccess(db)
	suite.dbAccess = dbAccess
}

func (suite *ClusterServiceDbAccessTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterServiceDbAccessTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterService, &model.K8sClusterServiceModel{})
}

func (suite *ClusterServiceDbAccessTestSuite) TestCreateClusterService() {
	t := suite.T()
	clusterService, err := suite.dbAccess.Create(clusterServiceSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterService.ID)
	assert.Equal(t, clusterServiceSample.CrdClusterID, clusterService.CrdClusterID)
	assert.Equal(t, clusterServiceSample.ComponentName, clusterService.ComponentName)
	assert.Equal(t, clusterServiceSample.ServiceName, clusterService.ServiceName)
	assert.Equal(t, clusterServiceSample.ServiceType, clusterService.ServiceType)
	assert.Equal(t, clusterServiceSample.Annotations, clusterService.Annotations)
	assert.Equal(t, clusterServiceSample.InternalAddrs, clusterService.InternalAddrs)
	assert.Equal(t, clusterServiceSample.ExternalAddrs, clusterService.ExternalAddrs)
	assert.Equal(t, clusterServiceSample.Domains, clusterService.Domains)
	assert.Equal(t, clusterServiceSample.Description, clusterService.Description)
}

func (suite *ClusterServiceDbAccessTestSuite) TestDeleteClusterService() {
	t := suite.T()
	clusterService, err := suite.dbAccess.Create(clusterServiceSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterService.ID)

	rows, err := suite.dbAccess.DeleteByID(clusterService.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterServiceDbAccessTestSuite) TestUpdateClusterService() {
	t := suite.T()
	clusterService, err := suite.dbAccess.Create(clusterServiceSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterService.ID)

	newClusterService := &model.K8sClusterServiceModel{
		ID:            clusterService.ID,
		CrdClusterID:  2,
		ComponentName: "updated-component",
		ServiceName:   "updated-service",
		ServiceType:   "NodePort",
		Annotations:   "updated-annotation=value",
		InternalAddrs: "test.updated",
		ExternalAddrs: "test.updated",
		Domains:       "www.example.com",
		Description:   "Updated service",
	}
	rows, err := suite.dbAccess.Update(newClusterService)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterServiceDbAccessTestSuite) TestGetClusterService() {
	t := suite.T()
	clusterService, err := suite.dbAccess.Create(clusterServiceSample)
	assert.NoError(t, err)
	assert.NotZero(t, clusterService.ID)

	foundClusterService, err := suite.dbAccess.FindByID(clusterService.ID)
	assert.NoError(t, err)
	assert.NotNil(t, foundClusterService)

	assert.Equal(t, clusterService.CrdClusterID, foundClusterService.CrdClusterID)
	assert.Equal(t, clusterService.ComponentName, foundClusterService.ComponentName)
	assert.Equal(t, clusterService.ServiceName, foundClusterService.ServiceName)
	assert.Equal(t, clusterService.ServiceType, foundClusterService.ServiceType)
	assert.Equal(t, clusterService.Annotations, foundClusterService.Annotations)
	assert.Equal(t, clusterService.InternalAddrs, foundClusterService.InternalAddrs)
	assert.Equal(t, clusterService.ExternalAddrs, foundClusterService.ExternalAddrs)
	assert.Equal(t, clusterService.Domains, foundClusterService.Domains)
	assert.Equal(t, clusterService.Description, foundClusterService.Description)
}

func TestClusterServiceDbAccess(t *testing.T) {
	suite.Run(t, new(ClusterServiceDbAccessTestSuite))
}

func (suite *ClusterServiceDbAccessTestSuite) TestFindByClusterID() {
	t := suite.T()
	svc1 := &model.K8sClusterServiceModel{
		CrdClusterID:  100,
		ComponentName: "mysql-comp",
		ServiceName:   "svc-1",
		ServiceType:   "ClusterIP",
	}
	svc2 := &model.K8sClusterServiceModel{
		CrdClusterID:  100,
		ComponentName: "mysql-comp",
		ServiceName:   "svc-2",
		ServiceType:   "LoadBalancer",
	}
	svc3 := &model.K8sClusterServiceModel{
		CrdClusterID:  200,
		ComponentName: "redis-comp",
		ServiceName:   "svc-3",
		ServiceType:   "ClusterIP",
	}
	_, err := suite.dbAccess.Create(svc1)
	assert.NoError(t, err)
	_, err = suite.dbAccess.Create(svc2)
	assert.NoError(t, err)
	_, err = suite.dbAccess.Create(svc3)
	assert.NoError(t, err)

	services, err := suite.dbAccess.FindByClusterID(100)
	assert.NoError(t, err)
	assert.Len(t, services, 2)

	serviceNames := map[string]bool{}
	for _, s := range services {
		serviceNames[s.ServiceName] = true
	}
	assert.True(t, serviceNames["svc-1"])
	assert.True(t, serviceNames["svc-2"])
}

func (suite *ClusterServiceDbAccessTestSuite) TestDeleteByClusterID() {
	t := suite.T()
	svc1 := &model.K8sClusterServiceModel{
		CrdClusterID:  100,
		ComponentName: "mysql-comp",
		ServiceName:   "svc-1",
		ServiceType:   "ClusterIP",
	}
	svc2 := &model.K8sClusterServiceModel{
		CrdClusterID:  100,
		ComponentName: "mysql-comp",
		ServiceName:   "svc-2",
		ServiceType:   "LoadBalancer",
	}
	_, err := suite.dbAccess.Create(svc1)
	assert.NoError(t, err)
	_, err = suite.dbAccess.Create(svc2)
	assert.NoError(t, err)

	rows, err := suite.dbAccess.DeleteByClusterID(100)
	assert.NoError(t, err)
	assert.Equal(t, uint64(2), rows)

	services, err := suite.dbAccess.FindByClusterID(100)
	assert.NoError(t, err)
	assert.Empty(t, services)
}

func (suite *ClusterServiceDbAccessTestSuite) TestDeleteByClusterIDAndServiceName() {
	t := suite.T()
	svc1 := &model.K8sClusterServiceModel{
		CrdClusterID:  100,
		ComponentName: "mysql-comp",
		ServiceName:   "svc-1",
		ServiceType:   "ClusterIP",
	}
	svc2 := &model.K8sClusterServiceModel{
		CrdClusterID:  100,
		ComponentName: "mysql-comp",
		ServiceName:   "svc-2",
		ServiceType:   "LoadBalancer",
	}
	_, err := suite.dbAccess.Create(svc1)
	assert.NoError(t, err)
	_, err = suite.dbAccess.Create(svc2)
	assert.NoError(t, err)

	rows, err := suite.dbAccess.DeleteByClusterIDAndServiceName(100, "svc-1")
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	services, err := suite.dbAccess.FindByClusterID(100)
	assert.NoError(t, err)
	assert.Len(t, services, 1)
	assert.Equal(t, "svc-2", services[0].ServiceName)
}
