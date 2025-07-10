// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package sinker

import (
	"database/sql"
	"encoding/base64"
	"fmt"
	"log"
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/spf13/cast"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
	"xorm.io/xorm"
)

func GetGormDB(dsn *InstanceDsn, sessionVars map[string]interface{}) (*gorm.DB, error) {
	dbc, err := GetConn(dsn, sessionVars)
	slowLogger := logger.New(
		//将标准输出作为Writer
		log.New(os.Stdout, "\r\n", log.LstdFlags),
		logger.Config{
			SlowThreshold: 0,
			LogLevel:      logger.Warn,
		},
	)

	db, err := gorm.Open(mysql.New(mysql.Config{
		Conn: dbc,
	}), &gorm.Config{
		DisableForeignKeyConstraintWhenMigrating: true,
		Logger:                                   slowLogger,
	})

	if err != nil {
		slog.Error("connect db", err)
		return nil, err
	}

	sqlDB, err := db.DB()
	if err != nil {
		slog.Error("get sql db", err)
		return nil, err
	}
	sqlDB.SetMaxOpenConns(2)
	sqlDB.SetMaxIdleConns(4)
	sqlDB.SetConnMaxLifetime(0)
	return db, nil
}

// GetConn 内置 var: charset,parseTime,loc,time_zone
func GetConn(dsn *InstanceDsn, sessionVars map[string]interface{}) (db *sql.DB, err error) {
	sessionParams := []string{}
	for k, v := range sessionVars {
		sessionParams = append(sessionParams, fmt.Sprintf("%s=%s", k,
			base64.URLEncoding.EncodeToString([]byte(cast.ToString(v)))))
	}
	tz := "loc=UTC&time_zone=%27%2B00%3A00%27" // we use UTC to get and set rather than Local
	sessionParams = append(sessionParams, tz)
	if dsn.Charset == "" {
		dsn.Charset = "utf8mb4"
	}

	dsnUrl := fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=%s&parseTime=True&%s",
		dsn.User,
		dsn.Password,
		dsn.Address,
		dsn.Database,
		dsn.Charset,
		strings.Join(sessionParams, "&"),
	)

	dbc, err := sql.Open("mysql", dsnUrl)
	if err != nil {
		log.Fatalf("connect to mysql failed %s", err.Error())
		return nil, err
	}
	return dbc, nil
}

func GetXormDB(dsn *InstanceDsn, sessionVars map[string]interface{}) (*xorm.Engine, error) {
	dsnUrl := fmt.Sprintf("%s:%s@tcp(%s)/%s?parseTime=True&loc=Local",
		dsn.User,
		dsn.Password,
		dsn.Address,
		dsn.Database,
	)
	engine, err := xorm.NewEngine("mysql", dsnUrl)
	if err != nil {
		log.Fatalf("connect to mysql failed %s", err.Error())
		return nil, err
	}
	// 连接池配置
	engine.SetMaxOpenConns(30)                  // 最大 db 连接
	engine.SetMaxIdleConns(10)                  // 最大 db 连接空闲数
	engine.SetConnMaxLifetime(30 * time.Minute) // 超过空闲数连接存活时间

	// 日志相关配置
	engine.ShowSQL(true) // 打印日志
	//engine.Logger().SetLevel(core.LOG_DEBUG) // 打印日志级别
	//engine.SetLogger()                       // 设置日志输出 (控制台, 日志文件, 系统日志等)

	// 测试连通性
	if err = engine.Ping(); err != nil {
		log.Fatalf("ping to db fail! err:%+v", err)
	}
	return engine, nil
}
