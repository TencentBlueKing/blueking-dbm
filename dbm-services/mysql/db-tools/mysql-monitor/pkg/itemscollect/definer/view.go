// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package definer

import (
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

func views(db *sqlx.DB) (msg []string, err error) {
	q, args, err := sqlx.In(
		`SELECT TABLE_NAME, TABLE_SCHEMA, DEFINER 
					FROM information_schema.VIEWS 
					WHERE TABLE_SCHEMA NOT IN (?)`,
		config.MonitorConfig.DBASysDbs,
	)
	if err != nil {
		return nil, errors.Wrap(err, "build In query view")
	}

	var res []struct {
		ViewName   string `db:"TABLE_NAME"`
		ViewSchema string `db:"TABLE_SCHEMA"`
		Definer    string `db:"DEFINER"`
	}
	err = db.Select(&res, db.Rebind(q), args...)
	if err != nil {
		return nil, errors.Wrap(err, "query views")
	}
	slog.Debug("query views", slog.Any("views", res))

	for _, ele := range res {
		owner := fmt.Sprintf(
			"view %s.%s",
			ele.ViewSchema, ele.ViewName,
		)
		if r := checkDefiner(owner, ele.Definer); r != "" {
			msg = append(msg, r)
		}
	}
	return msg, nil
}
