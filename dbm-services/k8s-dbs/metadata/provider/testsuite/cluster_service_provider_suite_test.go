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
	metaenitty "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/helper/testhelper"
	"k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"log"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

var k8sClusterServiceProvider = &metaenitty.K8sClusterServiceEntity{
	CrdClusterID:  uint64(1),
	ComponentName: "component_name_01",
	ServiceName:   "service_name_01",
	ServiceType:   "service_type_01",
	Annotations:   "annotations_01",
	InternalAddrs: "internal_addrs_01",
	ExternalAddrs: "external_addrs_01",
	Domains:       "domains_01",
	Description:   "description_01",
}

var k8sClusterServiceEntityList = []metaenitty.K8sClusterServiceEntity{
	{
		CrdClusterID:  uint64(1),
		ComponentName: "component_name_01",
		ServiceName:   "service_name_01",
		ServiceType:   "service_type_01",
		Annotations:   "annotations_01",
		InternalAddrs: "internal_addrs_01",
		ExternalAddrs: "external_addrs_01",
		Domains:       "domains_01",
		Description:   "description_01",
	},
	{
		CrdClusterID:  uint64(1),
		ComponentName: "component_name_01",
		ServiceName:   "service_name_01",
		ServiceType:   "service_type_01",
		Annotations:   "annotations_01",
		InternalAddrs: "internal_addrs_01",
		ExternalAddrs: "external_addrs_01",
		Domains:       "domains_01",
		Description:   "description_01",
	},
}

type ClusterServiceProviderTestSuite struct {
	suite.Suite
	mySqlContainer  *testhelper.MySQLContainerWrapper
	clusterProvider provider.K8sClusterServiceProvider
	ctx             context.Context
}

func (suite *ClusterServiceProviderTestSuite) SetupSuite() {
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
	clusterProvider := provider.GetK8sClusterServiceProvider(dbAccess)
	suite.clusterProvider = clusterProvider
}

func (suite *ClusterServiceProviderTestSuite) TearDownSuite() {
	if err := suite.mySqlContainer.Terminate(suite.ctx); err != nil {
		log.Fatalf("error terminating mysql container: %s", err)
	}
}

func (suite *ClusterServiceProviderTestSuite) SetupTest() {
	testhelper.InitTestTable(suite.mySqlContainer.ConnStr, constant.TbK8sClusterService, &model.K8sClusterServiceModel{})
}

func TestClusterServiceProvider(t *testing.T) {
	suite.Run(t, new(ClusterServiceProviderTestSuite))
}

func (suite *ClusterServiceProviderTestSuite) TestCreateClusterService() {
	t := suite.T()
	service, err := suite.clusterProvider.CreateClusterService(k8sClusterServiceProvider)
	assert.NoError(t, err)
	assert.Equal(t, k8sClusterServiceProvider.CrdClusterID, service.CrdClusterID)
	assert.Equal(t, k8sClusterServiceProvider.ComponentName, service.ComponentName)
	assert.Equal(t, k8sClusterServiceProvider.ServiceName, service.ServiceName)
	assert.Equal(t, k8sClusterServiceProvider.ServiceType, service.ServiceType)
	assert.Equal(t, k8sClusterServiceProvider.Annotations, service.Annotations)
	assert.Equal(t, k8sClusterServiceProvider.InternalAddrs, service.InternalAddrs)
	assert.Equal(t, k8sClusterServiceProvider.ExternalAddrs, service.ExternalAddrs)
	assert.Equal(t, k8sClusterServiceProvider.Domains, service.Domains)
	assert.Equal(t, k8sClusterServiceProvider.Description, service.Description)
}

func (suite *ClusterServiceProviderTestSuite) TestDeleteClusterServiceByID() {
	t := suite.T()
	service, err := suite.clusterProvider.CreateClusterService(k8sClusterServiceProvider)
	assert.NoError(t, err)
	assert.NotNil(t, service.ID)

	rows, err := suite.clusterProvider.DeleteClusterServiceByID(service.ID)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterServiceProviderTestSuite) TestFindClusterServiceByID() {
	t := suite.T()
	service, err := suite.clusterProvider.CreateClusterService(k8sClusterServiceProvider)
	assert.NoError(t, err)
	assert.NotNil(t, service.ID)

	foundService, err := suite.clusterProvider.FindClusterServiceByID(service.ID)
	assert.NoError(t, err)
	assert.Equal(t, service.ID, foundService.ID)
	assert.Equal(t, k8sClusterServiceProvider.CrdClusterID, foundService.CrdClusterID)
	assert.Equal(t, k8sClusterServiceProvider.ComponentName, foundService.ComponentName)
	assert.Equal(t, k8sClusterServiceProvider.ServiceName, foundService.ServiceName)
	assert.Equal(t, k8sClusterServiceProvider.ServiceType, foundService.ServiceType)
	assert.Equal(t, k8sClusterServiceProvider.Annotations, foundService.Annotations)
	assert.Equal(t, k8sClusterServiceProvider.InternalAddrs, foundService.InternalAddrs)
	assert.Equal(t, k8sClusterServiceProvider.ExternalAddrs, foundService.ExternalAddrs)
	assert.Equal(t, k8sClusterServiceProvider.Domains, foundService.Domains)
	assert.Equal(t, k8sClusterServiceProvider.Description, foundService.Description)
}

func (suite *ClusterServiceProviderTestSuite) TestUpdateClusterService() {
	t := suite.T()
	service, err := suite.clusterProvider.CreateClusterService(k8sClusterServiceProvider)
	assert.NoError(t, err)
	assert.NotNil(t, service.ID)

	service.Description = "updated_description"
	rows, err := suite.clusterProvider.UpdateClusterService(service)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func (suite *ClusterServiceProviderTestSuite) TestFindByClusterID() {
	t := suite.T()
	svc1 := &metaenitty.K8sClusterServiceEntity{
		CrdClusterID:  uint64(300),
		ComponentName: "comp-a",
		ServiceName:   "svc-a",
		ServiceType:   "ClusterIP",
	}
	svc2 := &metaenitty.K8sClusterServiceEntity{
		CrdClusterID:  uint64(300),
		ComponentName: "comp-a",
		ServiceName:   "svc-b",
		ServiceType:   "LoadBalancer",
	}
	_, err := suite.clusterProvider.CreateClusterService(svc1)
	assert.NoError(t, err)
	_, err = suite.clusterProvider.CreateClusterService(svc2)
	assert.NoError(t, err)

	services, err := suite.clusterProvider.FindByClusterID(300)
	assert.NoError(t, err)
	assert.Len(t, services, 2)

	names := map[string]bool{}
	for _, s := range services {
		names[s.ServiceName] = true
	}
	assert.True(t, names["svc-a"])
	assert.True(t, names["svc-b"])
}

func (suite *ClusterServiceProviderTestSuite) TestDeleteByClusterID() {
	t := suite.T()
	svc1 := &metaenitty.K8sClusterServiceEntity{
		CrdClusterID:  uint64(400),
		ComponentName: "comp-a",
		ServiceName:   "svc-a",
		ServiceType:   "ClusterIP",
	}
	svc2 := &metaenitty.K8sClusterServiceEntity{
		CrdClusterID:  uint64(400),
		ComponentName: "comp-a",
		ServiceName:   "svc-b",
		ServiceType:   "LoadBalancer",
	}
	_, err := suite.clusterProvider.CreateClusterService(svc1)
	assert.NoError(t, err)
	_, err = suite.clusterProvider.CreateClusterService(svc2)
	assert.NoError(t, err)

	rows, err := suite.clusterProvider.DeleteByClusterID(400)
	assert.NoError(t, err)
	assert.Equal(t, uint64(2), rows)

	services, err := suite.clusterProvider.FindByClusterID(400)
	assert.NoError(t, err)
	assert.Empty(t, services)
}

func (suite *ClusterServiceProviderTestSuite) TestDeleteByClusterIDAndServiceName() {
	t := suite.T()
	svc1 := &metaenitty.K8sClusterServiceEntity{
		CrdClusterID:  uint64(500),
		ComponentName: "comp-a",
		ServiceName:   "svc-a",
		ServiceType:   "ClusterIP",
	}
	svc2 := &metaenitty.K8sClusterServiceEntity{
		CrdClusterID:  uint64(500),
		ComponentName: "comp-a",
		ServiceName:   "svc-b",
		ServiceType:   "LoadBalancer",
	}
	_, err := suite.clusterProvider.CreateClusterService(svc1)
	assert.NoError(t, err)
	_, err = suite.clusterProvider.CreateClusterService(svc2)
	assert.NoError(t, err)

	rows, err := suite.clusterProvider.DeleteByClusterIDAndServiceName(500, "svc-a")
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)

	services, err := suite.clusterProvider.FindByClusterID(500)
	assert.NoError(t, err)
	assert.Len(t, services, 1)
	assert.Equal(t, "svc-b", services[0].ServiceName)
}

func (suite *ClusterServiceProviderTestSuite) TestUpsertClusterServices() {
	t := suite.T()
	// First upsert: insert 2 services
	entities1 := []*metaenitty.K8sClusterServiceEntity{
		{
			CrdClusterID:  uint64(600),
			ComponentName: "comp-a",
			ServiceName:   "svc-a",
			ServiceType:   "ClusterIP",
			InternalAddrs: "svc-a.ns.svc.cluster.local:3306",
		},
		{
			CrdClusterID:  uint64(600),
			ComponentName: "comp-a",
			ServiceName:   "svc-b",
			ServiceType:   "LoadBalancer",
			ExternalAddrs: "svc-b.ns.svc.external:3306",
		},
	}
	err := suite.clusterProvider.UpsertClusterServices(600, entities1)
	assert.NoError(t, err)

	services, err := suite.clusterProvider.FindByClusterID(600)
	assert.NoError(t, err)
	assert.Len(t, services, 2)

	// Second upsert: replace with different data
	entities2 := []*metaenitty.K8sClusterServiceEntity{
		{
			CrdClusterID:  uint64(600),
			ComponentName: "comp-b",
			ServiceName:   "svc-c",
			ServiceType:   "NodePort",
			InternalAddrs: "svc-c.ns.svc.cluster.local:6379",
		},
	}
	err = suite.clusterProvider.UpsertClusterServices(600, entities2)
	assert.NoError(t, err)

	services, err = suite.clusterProvider.FindByClusterID(600)
	assert.NoError(t, err)
	assert.Len(t, services, 1)
	assert.Equal(t, "svc-c", services[0].ServiceName)
	assert.Equal(t, "comp-b", services[0].ComponentName)
}
