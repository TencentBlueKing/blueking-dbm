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
	"fmt"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	"k8s-dbs/metadata/dbaccess/model"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func InitK8sClusterServiceTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_cluster_service;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_cluster_service table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sClusterServiceModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_cluster_service table")
		return nil, err
	}
	return db, nil
}

func TestCreateService(t *testing.T) {
	db, err := InitK8sClusterServiceTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterServiceDbAccess(db)

	service := &model.K8sClusterServiceModel{
		CrdClusterID:  1,
		ComponentName: "test-component",
		ServiceName:   "test-service",
		ServiceType:   "LoadBalancer",
		Annotations:   "{xxxxxx:xxxxxx}",
		InternalAddrs: "ip1:8080;ip2:8081",
		ExternalAddrs: "ip3:8080;ip3:8081",
		Domains:       "test-domain1;test-domain2",
		Description:   "desc",
	}

	added, err := dbAccess.Create(service)
	assert.NoError(t, err)

	assert.Equal(t, service.CrdClusterID, added.CrdClusterID)
	assert.Equal(t, service.ComponentName, added.ComponentName)
	assert.Equal(t, service.ServiceName, added.ServiceName)
	assert.Equal(t, service.ServiceType, added.ServiceType)
	assert.Equal(t, service.Annotations, added.Annotations)
	assert.Equal(t, service.InternalAddrs, added.InternalAddrs)
	assert.Equal(t, service.ExternalAddrs, added.ExternalAddrs)
	assert.Equal(t, service.Domains, added.Domains)
}

func TestGetService(t *testing.T) {
	db, err := InitK8sClusterServiceTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterServiceDbAccess(db)

	service := &model.K8sClusterServiceModel{
		CrdClusterID:  1,
		ComponentName: "test-component",
		ServiceName:   "test-service",
		ServiceType:   "LoadBalancer",
		Annotations:   "{xxxxxx:xxxxxx}",
		InternalAddrs: "ip1:8080;ip2:8081",
		ExternalAddrs: "ip3:8080;ip3:8081",
		Domains:       "test-domain1;test-domain2",
		Description:   "desc",
	}

	_, err = dbAccess.Create(service)
	assert.NoError(t, err)

	founded, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, service.CrdClusterID, founded.CrdClusterID)
	assert.Equal(t, service.ComponentName, founded.ComponentName)
	assert.Equal(t, service.ServiceName, founded.ServiceName)
	assert.Equal(t, service.ServiceType, founded.ServiceType)
	assert.Equal(t, service.Annotations, founded.Annotations)
	assert.Equal(t, service.InternalAddrs, founded.InternalAddrs)
	assert.Equal(t, service.ExternalAddrs, founded.ExternalAddrs)
	assert.Equal(t, service.Domains, founded.Domains)
}
