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
	"time"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func SetUpTestDBForCmpv() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_componentversion;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_componentversion table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdComponentVersionModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_componentversion table")
		return nil, err
	}
	return db, nil
}

func TestCreateComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpvDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	addedCmpv, err := dbAccess.Create(cmpv)
	assert.NoError(t, err)

	assert.Equal(t, cmpv.ComponentVersionName, addedCmpv.ComponentVersionName)
	assert.Equal(t, cmpv.AddonID, addedCmpv.AddonID)
	assert.Equal(t, cmpv.Metadata, addedCmpv.Metadata)
	assert.Equal(t, cmpv.Spec, addedCmpv.Spec)
	assert.Equal(t, cmpv.Active, addedCmpv.Active)
}

func TestDeleteComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpvDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	_, err = dbAccess.Create(cmpv)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpvDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	_, err = dbAccess.Create(cmpv)
	assert.NoError(t, err)

	updatedCmpv := &model.K8sCrdComponentVersionModel{
		ID:                   1,
		ComponentVersionName: "mycmpv2",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default2\"}",
		Spec:                 "{\"replicas\":2}",
		Active:               false,
		Description:          "desc",
		UpdatedAt:            time.Now(),
	}
	rows, err := dbAccess.Update(updatedCmpv)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetComponentVersion(t *testing.T) {
	db, err := SetUpTestDBForCmpv()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdCmpvDbAccess(db)

	cmpv := &model.K8sCrdComponentVersionModel{
		ComponentVersionName: "mycmpv",
		AddonID:              uint64(1),
		Metadata:             "{\"namespace\":\"default\"}",
		Spec:                 "{\"replicas\":3}",
		Active:               true,
		Description:          "desc",
	}

	_, err = dbAccess.Create(cmpv)
	assert.NoError(t, err)

	foundCmpv, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, cmpv.ComponentVersionName, foundCmpv.ComponentVersionName)
	assert.Equal(t, cmpv.AddonID, foundCmpv.AddonID)
	assert.Equal(t, cmpv.Metadata, foundCmpv.Metadata)
	assert.Equal(t, cmpv.Spec, foundCmpv.Spec)
	assert.Equal(t, cmpv.Active, foundCmpv.Active)
}
