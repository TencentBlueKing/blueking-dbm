// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package consumer

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"log/slog"
	"os"
	"strings"

	"github.com/spf13/cast"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

type messageWrapper struct {
	Items []struct {
		Data json.RawMessage `json:"data"`
	} `json:"items"`
}

// getDb
// doris: group_commit enable_insert_strict=false insert_max_filter_ratio=1
// SET group_commit = async_mode; SET enable_insert_strict=false;
func getDb(s *Sinker) (*gorm.DB, error) {
	sessionParams := []string{}
	for k, v := range s.RuntimeConfig.Dsn.SessionVariables {
		sessionParams = append(sessionParams, fmt.Sprintf("%s=%s", k,
			base64.URLEncoding.EncodeToString([]byte(cast.ToString(v)))))
	}
	tz := "loc=UTC&time_zone=%27%2B00%3A00%27" // we use UTC to get and set
	sessionParams = append(sessionParams, tz)

	dsn := fmt.Sprintf(
		`%s:%s@tcp(%s)/%s?charset=%s&parseTime=True&%s`,
		s.RuntimeConfig.Dsn.User,
		s.RuntimeConfig.Dsn.Password,
		s.RuntimeConfig.Dsn.Address,
		s.RuntimeConfig.Dsn.Database,
		s.RuntimeConfig.Dsn.Charset,
		strings.Join(sessionParams, "&"),
	)
	slowLogger := logger.New(
		//将标准输出作为Writer
		log.New(os.Stdout, "\r\n", log.LstdFlags),
		logger.Config{
			SlowThreshold: 0,
			LogLevel:      logger.Warn,
		},
	)

	db, err := gorm.Open(
		mysql.New(
			mysql.Config{
				DSN: dsn,
			},
		),
		&gorm.Config{
			Logger: slowLogger,
		},
	)

	if err != nil {
		slog.Error("connect db", err)
		return nil, err
	}

	sqlDB, err := db.DB()
	if err != nil {
		slog.Error("get sql db", err)
		return nil, err
	}
	sqlDB.SetMaxOpenConns(s.RuntimeConfig.Dsn.ConnectionPerPartition)
	sqlDB.SetMaxIdleConns(2 * s.RuntimeConfig.Dsn.ConnectionPerPartition)
	sqlDB.SetConnMaxLifetime(0)
	return db, nil
}
