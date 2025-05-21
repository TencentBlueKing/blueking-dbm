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

func InitRequestRecordTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_cluster_request_record;").Error; err != nil {
		fmt.Println("Failed to drop tb_cluster_request_record table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.ClusterRequestRecordModel{}); err != nil {
		fmt.Println("Failed to migrate tb_cluster_request_record table")
		return nil, err
	}
	return db, nil
}

func TestCreateRequest(t *testing.T) {
	db, err := InitRequestRecordTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewClusterRequestRecordDbAccess(db)

	request := &model.ClusterRequestRecordModel{
		RequestID:     "test-request-id",
		RequestParams: "test params",
		RequestType:   "Create",
		Description:   "desc",
		CreatedBy:     "Admin",
	}

	added, err := dbAccess.Create(request)
	assert.NoError(t, err, "Failed to create request")
	fmt.Printf("Created request %+v\n", added)

	var founded model.ClusterRequestRecordModel
	err = db.First(&founded, "request_id=?", request.RequestID).Error
	assert.NoError(t, err, "Failed to query request")
	assert.Equal(t, request.RequestID, founded.RequestID)
	assert.Equal(t, request.RequestParams, founded.RequestParams)
	assert.Equal(t, request.RequestType, founded.RequestType)
	assert.Equal(t, request.Description, founded.Description)
	assert.Equal(t, request.CreatedBy, founded.CreatedBy)
}

func TestGetRequest(t *testing.T) {
	db, err := InitK8sClusterConfigTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewClusterRequestRecordDbAccess(db)

	request := &model.ClusterRequestRecordModel{
		RequestID:     "test-request-id",
		RequestParams: "test params",
		RequestType:   "Create",
		Description:   "desc",
		CreatedBy:     "Admin",
	}

	added, err := dbAccess.Create(request)
	assert.NoError(t, err, "Failed to create request")
	fmt.Printf("Created request %+v\n", added)

	founded, err := dbAccess.FindByID(1)
	assert.NoError(t, err, "Failed to query request")
	assert.Equal(t, request.RequestID, founded.RequestID)
	assert.Equal(t, request.RequestParams, founded.RequestParams)
	assert.Equal(t, request.RequestType, founded.RequestType)
	assert.Equal(t, request.Description, founded.Description)
	assert.Equal(t, request.CreatedBy, founded.CreatedBy)
}
