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

func InitK8sClusterConfigTable() (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		fmt.Println("Failed to connect to database")
		return nil, err
	}
	if err := db.Exec("DROP TABLE IF EXISTS tb_k8s_cluster_config;").Error; err != nil {
		fmt.Println("Failed to drop tb_k8s_cluster_config table")
		return nil, err
	}
	if err := db.AutoMigrate(&model.K8sClusterConfigModel{}); err != nil {
		fmt.Println("Failed to migrate tb_k8s_cluster_config table")
		return nil, err
	}
	return db, nil
}

func TestCreateK8sClusterConfig(t *testing.T) {
	db, err := InitK8sClusterConfigTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	config := &model.K8sClusterConfigModel{
		ClusterName:  "BCS-K8S-000",
		APIServerURL: "https://127.0.0.1:60002",
		CACert:       "test_ca_cert",
		ClientCert:   "test_client_cert",
		ClientKey:    "test_client_key",
		Token:        "test_token",
		Username:     "test_username",
		Password:     "test_password",
		Description:  "desc",
	}

	added, err := dbAccess.Create(config)
	assert.NoError(t, err, "Failed to create config")
	fmt.Printf("Created config %+v\n", added)

	var founded model.K8sClusterConfigModel
	err = db.First(&founded, "cluster_name=?", "BCS-K8S-000").Error
	assert.NoError(t, err, "Failed to query config")
	assert.Equal(t, config.ClusterName, founded.ClusterName)
	assert.Equal(t, config.APIServerURL, founded.APIServerURL)
	assert.Equal(t, config.CACert, founded.CACert)
	assert.Equal(t, config.ClientCert, founded.ClientCert)
	assert.Equal(t, config.ClientKey, founded.ClientKey)
	assert.Equal(t, config.Token, founded.Token)
	assert.Equal(t, config.Username, founded.Username)
	assert.Equal(t, config.Password, founded.Password)
}

func TestDeleteK8sClusterConfig(t *testing.T) {
	db, err := InitK8sClusterConfigTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	config := &model.K8sClusterConfigModel{
		ClusterName:  "BCS-K8S-000",
		APIServerURL: "https://127.0.0.1:60002",
		CACert:       "test_ca_cert",
		ClientCert:   "test_client_cert",
		ClientKey:    "test_client_key",
		Token:        "test_token",
		Username:     "test_username",
		Password:     "test_password",
		Description:  "desc",
	}

	added, err := dbAccess.Create(config)
	assert.NoError(t, err, "Failed to create config")
	fmt.Printf("Created config %+v\n", added)

	rows, err := dbAccess.DeleteByID(1)
	assert.NoError(t, err, "Failed to delete config")
	assert.Equal(t, uint64(1), rows)
}

func TestUpdateK8sClusterConfig(t *testing.T) {
	db, err := InitK8sClusterConfigTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	config := &model.K8sClusterConfigModel{
		ClusterName:  "BCS-K8S-000",
		APIServerURL: "https://127.0.0.1:60002",
		CACert:       "test_ca_cert",
		ClientCert:   "test_client_cert",
		ClientKey:    "test_client_key",
		Token:        "test_token",
		Username:     "test_username",
		Password:     "test_password",
		Description:  "desc",
	}

	added, err := dbAccess.Create(config)
	assert.NoError(t, err, "Failed to create config")
	fmt.Printf("Created config %+v\n", added)

	newConfig := &model.K8sClusterConfigModel{
		ID:           1,
		ClusterName:  "BCS-K8S-001",
		APIServerURL: "https://127.0.0.1:60001",
		CACert:       "test_ca_cert1",
		ClientCert:   "test_client_cert1",
		ClientKey:    "test_client_key1",
		Token:        "test_token1",
		Username:     "test_username1",
		Password:     "test_password1",
		Description:  "desc1",
	}
	rows, err := dbAccess.Update(newConfig)
	assert.NoError(t, err, "Failed to update config")
	assert.Equal(t, uint64(1), rows)
}

func TestGetK8sClusterConfig(t *testing.T) {
	db, err := InitK8sClusterConfigTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	config := &model.K8sClusterConfigModel{
		ClusterName:  "BCS-K8S-000",
		APIServerURL: "https://127.0.0.1:60002",
		CACert:       "test_ca_cert",
		ClientCert:   "test_client_cert",
		ClientKey:    "test_client_key",
		Token:        "test_token",
		Username:     "test_username",
		Password:     "test_password",
		Description:  "desc",
	}

	added, err := dbAccess.Create(config)
	assert.NoError(t, err, "Failed to create config")
	fmt.Printf("Created config %+v\n", added)

	founded, err := dbAccess.FindByID(1)
	assert.NoError(t, err, "Failed to find config")
	assert.Equal(t, config.ClusterName, founded.ClusterName)
	assert.Equal(t, config.APIServerURL, founded.APIServerURL)
	assert.Equal(t, config.CACert, founded.CACert)
	assert.Equal(t, config.ClientCert, founded.ClientCert)
	assert.Equal(t, config.ClientKey, founded.ClientKey)
	assert.Equal(t, config.Token, founded.Token)
	assert.Equal(t, config.Username, founded.Username)
	assert.Equal(t, config.Password, founded.Password)
}

func TestGetK8sClusterConfigByName(t *testing.T) {
	db, err := InitK8sClusterConfigTable()
	assert.NoError(t, err)

	dbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	config := &model.K8sClusterConfigModel{
		ClusterName:  "BCS-K8S-000",
		APIServerURL: "https://127.0.0.1:60002",
		CACert:       "test_ca_cert",
		ClientCert:   "test_client_cert",
		ClientKey:    "test_client_key",
		Token:        "test_token",
		Username:     "test_username",
		Password:     "test_password",
		Description:  "desc",
	}

	added, err := dbAccess.Create(config)
	assert.NoError(t, err, "Failed to create config")
	fmt.Printf("Created config %+v\n", added)

	founded, err := dbAccess.FindByClusterName(config.ClusterName)
	assert.NoError(t, err, "Failed to find config")
	assert.Equal(t, config.ClusterName, founded.ClusterName)
	assert.Equal(t, config.APIServerURL, founded.APIServerURL)
	assert.Equal(t, config.CACert, founded.CACert)
	assert.Equal(t, config.ClientCert, founded.ClientCert)
	assert.Equal(t, config.ClientKey, founded.ClientKey)
	assert.Equal(t, config.Token, founded.Token)
	assert.Equal(t, config.Username, founded.Username)
	assert.Equal(t, config.Password, founded.Password)
}
