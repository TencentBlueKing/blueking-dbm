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

func initClusterTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_crd_cluster;").Error; err != nil {
		fmt.Println("Failed to drop k8s_crd_clusters table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sCrdClusterModel{}); err != nil {
		fmt.Println("Failed to migrate k8s_crd_clusters table")
		return nil, err
	}
	return db, nil
}

func TestCreateCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)

	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Namespace:          "default",
		Status:             "Enable",
		Description:        "desc",
	}

	added, err := dbAccess.Create(cluster)
	assert.NoError(t, err)
	assert.Equal(t, cluster.ClusterName, added.ClusterName)
	assert.Equal(t, cluster.Namespace, added.Namespace)
	assert.Equal(t, cluster.Status, added.Status)
	assert.Equal(t, cluster.AddonID, added.AddonID)
}

func TestDeleteCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Status:             "Enable",
		Description:        "desc",
	}
	_, err = dbAccess.Create(cluster)
	assert.NoError(t, err)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Status:             "Enable",
		Description:        "desc",
	}
	_, err = dbAccess.Create(cluster)
	assert.NoError(t, err)

	newCluster := &model.K8sCrdClusterModel{
		ID:          1,
		ClusterName: "mycluster2",
		Namespace:   "default2",
		Status:      "Disable",
		Description: "desc desc",
		UpdatedAt:   time.Now(),
	}
	rows, err := dbAccess.Update(newCluster)
	assert.NoError(t, err)
	assert.Equal(t, uint64(1), rows)
}

func TestGetCluster(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Status:             "Enable",
		Description:        "desc",
	}
	_, err = dbAccess.Create(cluster)
	assert.NoError(t, err)

	findCluster, err := dbAccess.FindByID(1)
	assert.NoError(t, err)
	assert.Equal(t, cluster.ClusterName, findCluster.ClusterName)
	assert.Equal(t, cluster.Namespace, findCluster.Namespace)
	assert.Equal(t, cluster.Status, findCluster.Status)
	assert.Equal(t, cluster.AddonID, findCluster.AddonID)
}

func TestGetClusterByParams(t *testing.T) {
	db, err := initClusterTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewCrdClusterDbAccess(db)
	cluster := &model.K8sCrdClusterModel{
		ClusterName:        "mycluster",
		Namespace:          "default",
		K8sClusterConfigID: 1,
		RequestID:          "1",
		Status:             "Enable",
		Description:        "desc",
	}
	_, err = dbAccess.Create(cluster)
	assert.NoError(t, err)

	params := map[string]interface{}{
		"k8s_cluster_config_id": 1,
		"cluster_name":          "mycluster",
		"namespace":             "default",
	}
	findCluster, err := dbAccess.FindByParams(params)
	assert.NoError(t, err)
	assert.Equal(t, cluster.ClusterName, findCluster.ClusterName)
	assert.Equal(t, cluster.Namespace, findCluster.Namespace)
	assert.Equal(t, cluster.Status, findCluster.Status)
	assert.Equal(t, cluster.AddonID, findCluster.AddonID)
}
