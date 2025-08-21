// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlconn

import (
	"context"
	"database/sql"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
)

// GetMysqlDataSize 获取mysql数据大小, 单位MB
func GetMysqlDataSize(db *sql.DB) (float64, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	var (
		dataDirQuery       = `show global variables like 'datadir'`
		tokudbDataDirQuery = `show global variables like 'tokudb_data_dir'`
	)
	var (
		datadirPath       string
		tokudbDatadirPath string
		field             string
	)

	err := db.QueryRowContext(ctx, dataDirQuery).Scan(&field, &datadirPath)
	if err != nil || len(datadirPath) == 0 {
		return 0, errors.New("db fail to get variables datadir")
	}
	err = db.QueryRowContext(ctx, tokudbDataDirQuery).Scan(&field, &tokudbDatadirPath)
	if err != nil || len(tokudbDatadirPath) == 0 {
		tokudbDatadirPath = ""
	}

	pathList := []string{}
	if datadirPath != "" {
		pathList = append(pathList, datadirPath)
	}
	if tokudbDatadirPath != "" {
		pathList = append(pathList, tokudbDatadirPath)
	}

	return cmutil.DoDuCmd(pathList)
}
