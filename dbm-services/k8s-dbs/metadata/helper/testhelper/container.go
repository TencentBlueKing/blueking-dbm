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

package testhelper

import (
	"context"
	"fmt"
	"log"
	"log/slog"

	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/modules/mysql"
	"github.com/testcontainers/testcontainers-go/wait"
	mysqldriver "gorm.io/driver/mysql"
	"gorm.io/gorm"
)

// MySQLContainerWrapper mysql 容器包装结构体
type MySQLContainerWrapper struct {
	*mysql.MySQLContainer
	ConnStr string
}

// NewMySQLContainerWrapper 构建 MySQLContainerWrapper
func NewMySQLContainerWrapper(ctx context.Context) (*MySQLContainerWrapper, error) {
	mySQLContainer, err := mysql.Run(ctx,
		"mysql:8.0.36",
		mysql.WithDatabase("bkbase_dbs"),
		mysql.WithUsername("root"),
		mysql.WithPassword("TestPwd123"),
		testcontainers.WithWaitStrategy(
			wait.ForListeningPort("3306/tcp")),
	)
	if err != nil {
		return nil, err
	}
	connStr, err := mySQLContainer.ConnectionString(ctx,
		"charset=utf8mb4",
		"parseTime=True",
		"loc=Local",
	)
	slog.Info("Print connStr", "connStr", connStr)
	if err != nil {
		return nil, err
	}
	return &MySQLContainerWrapper{
		MySQLContainer: mySQLContainer,
		ConnStr:        connStr,
	}, nil
}

// InitDBConnection 初始化 DB 连接
func InitDBConnection(connStr string) (*gorm.DB, error) {
	db, err := gorm.Open(mysqldriver.Open(connStr), &gorm.Config{})
	if err != nil {
		log.Fatal(err)
	}
	return db, nil
}

// InitTestTable 初始化测试表
func InitTestTable(connStr string, table string, modelPtr interface{}) {
	db, err := gorm.Open(mysqldriver.Open(connStr), &gorm.Config{})
	if err != nil {
		log.Fatal(err)
	}
	sql := fmt.Sprintf("DROP TABLE IF EXISTS %s;", table)
	if err := db.Exec(sql).Error; err != nil {
		log.Fatal(err)
	}
	if err := db.AutoMigrate(modelPtr); err != nil {
		log.Fatal(err)
	}
}
