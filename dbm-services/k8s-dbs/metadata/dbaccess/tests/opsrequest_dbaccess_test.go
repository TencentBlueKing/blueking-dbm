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
	"k8s-dbs/metadata/model"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func InitOpsTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_opsrequest;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_crd_opsrequest table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdOpsRequestModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_crd_opsrequest table")
		return nil, err
	}
	return db, nil
}

func TestCreateOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	var foundOps model.K8sCrdOpsRequestModel
	err = db.First(&foundOps, "opsrequest_name=?", "greptimedb-restart").Error
	assert.NoError(t, err, "Failed to query ops")
	assert.Equal(t, ops.OpsRequestName, foundOps.OpsRequestName)
	assert.Equal(t, ops.OpsRequestType, foundOps.OpsRequestType)
	assert.Equal(t, ops.K8sClusterConfigID, foundOps.K8sClusterConfigID)
	assert.Equal(t, ops.RequestID, foundOps.RequestID)
	assert.Equal(t, ops.CrdClusterID, foundOps.CrdClusterID)
	assert.Equal(t, ops.Metadata, foundOps.Metadata)
	assert.Equal(t, ops.Status, foundOps.Status)
	assert.Equal(t, ops.Spec, foundOps.Spec)
}

func TestDeleteOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err, "Failed to delete ops")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	newOps := &model.K8sCrdOpsRequestModel{
		ID:             1,
		OpsRequestName: "greptimedb-restart",
		OpsRequestType: "Start",
		CrdClusterID:   1,
		Metadata:       "{\"namespace\":\"default\"}",
		Spec:           "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:         "Finished",
		Description:    "desc",
	}
	rows, err := dbAccess.Update(newOps)
	assert.NoError(t, err, "Failed to update ops")
	assert.Equal(t, uint64(1), rows)
}

func TestGetOps(t *testing.T) {
	db, err := InitOpsTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)

	ops := &model.K8sCrdOpsRequestModel{
		OpsRequestName:     "greptimedb-restart",
		OpsRequestType:     "Start",
		CrdClusterID:       1,
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Metadata:           "{\"namespace\":\"default\"}",
		Spec:               "{\"clusterName\":\"gt-cluster\", \"type\":\"Start\"}",
		Status:             "Creating",
		Description:        "desc",
	}

	addedOps, err := dbAccess.Create(ops)
	assert.NoError(t, err, "Failed to create ops")
	fmt.Printf("Created ops %+v\n", addedOps)

	foundOps, err := dbAccess.FindByID(1)
	assert.NoError(t, err, "Failed to find ops")
	assert.NoError(t, err, "Failed to query ops")
	assert.Equal(t, ops.OpsRequestName, foundOps.OpsRequestName)
	assert.Equal(t, ops.OpsRequestType, foundOps.OpsRequestType)
	assert.Equal(t, ops.CrdClusterID, foundOps.CrdClusterID)
	assert.Equal(t, ops.K8sClusterConfigID, foundOps.K8sClusterConfigID)
	assert.Equal(t, ops.RequestID, foundOps.RequestID)
	assert.Equal(t, ops.Metadata, foundOps.Metadata)
	assert.Equal(t, ops.Status, foundOps.Status)
	assert.Equal(t, ops.Spec, foundOps.Spec)
}
