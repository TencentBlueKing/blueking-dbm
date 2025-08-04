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

package util

import (
	"fmt"
	"k8s-dbs/metadata/constant"
	"k8s-dbs/metadata/dbaccess"
	metamodel "k8s-dbs/metadata/model"
	"log/slog"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

// InitTestTable 初始化测试表
func InitTestTable(table string, modelPtr interface{}) (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(constant.MySQLTestURL), &gorm.Config{})
	if err != nil {
		slog.Error("failed to connect database", "err", err)
		return nil, err
	}
	sql := fmt.Sprintf("DROP TABLE IF EXISTS %s;", table)

	if err := db.Exec(sql).Error; err != nil {
		slog.Error("failed to drop table", "err", err)
		return nil, err
	}
	if err := db.AutoMigrate(modelPtr); err != nil {
		slog.Error("failed to migrate table", "err", err)
		return nil, err
	}
	return db, nil
}

// GetAcVersionTestDbAccess 获取测试 AddonClusterVersionDbAccess
func GetAcVersionTestDbAccess() dbaccess.AddonClusterVersionDbAccess {
	db, err := InitTestTable(constant.TbAddonClusterVersion, &metamodel.AddonClusterVersionModel{})
	if err != nil {
		panic(err)
	}
	dbAccess := dbaccess.NewAddonClusterVersionDbAccess(db)
	return dbAccess
}

// GetClusterTagTestDbAccess 获取测试 ClusterTagTestDbAccess
func GetClusterTagTestDbAccess() dbaccess.K8sCrdClusterTagDbAccess {
	db, err := InitTestTable(constant.TbK8sCrdClusterTag, &metamodel.K8sCrdClusterTagModel{})
	if err != nil {
		panic(err)
	}
	dbAccess := dbaccess.NewK8sCrdClusterTagDbAccess(db)
	return dbAccess
}

// GetAddonCategoryTestDbAccess 获取测试 AddonCategoryDbAccess
func GetAddonCategoryTestDbAccess() dbaccess.AddonCategoryDbAccess {
	db, err := InitTestTable(constant.TbAddonCategory, &metamodel.AddonCategoryModel{})
	if err != nil {
		panic(err)
	}
	dbAccess := dbaccess.NewAddonCategoryDbAccess(db)
	return dbAccess
}
