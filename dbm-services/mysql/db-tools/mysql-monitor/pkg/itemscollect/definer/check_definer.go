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
	"slices"
	"strings"
)

func checkDefiner(ownerFinger string, definer string) string {
	slog.Debug(
		"check definer",
		slog.String("owner", ownerFinger), slog.String("definer", definer),
	)

	splitDefiner := strings.Split(definer, `@`)
	definerUserName := splitDefiner[0]
	definerHost := splitDefiner[1]

	var msgSlice []string
	if slices.Index(mysqlUsers, definerUserName) < 0 {
		msgSlice = append(
			msgSlice,
			fmt.Sprintf("username %s not exists", definerUserName),
		)
	}
	if definerHost != "localhost" {
		msgSlice = append(
			msgSlice,
			fmt.Sprintf("host %s not localhost", definerHost),
		)
	}
	if len(msgSlice) > 0 {
		return fmt.Sprintf(
			"%s definer %s",
			ownerFinger,
			strings.Join(msgSlice, ","),
		)
	}
	return ""
}
