// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package identifiertrans

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil/identifiertrans/internal/tables"
	"fmt"
)

func TablenameToFilename(tablename string) (filename string) {
	for _, c := range tablename {
		if c < 128 && tables.SafeChar[c] {
			filename += string(c)
			continue
		}

		filename += "@"

		if (c >= 0x00C0 && c <= 0x05FF) ||
			(c >= 0x1E00 && c <= 0x1FFF) ||
			(c >= 0x2160 && c <= 0x217F) ||
			(c >= 0x24B0 && c <= 0x24EF) ||
			(c >= 0xFF20 && c <= 0xFF5F) {
			var code rune
			if c >= 0x00C0 && c <= 0x05FF {
				code = tables.Uni0c0005ff[c-0x00C0]
			} else if c >= 0x1E00 && c <= 0x1FFF {
				code = tables.Uni1e001fff[c-0x1E00]
			} else if c >= 0x2160 && c <= 0x217F {
				code = tables.Uni2160217f[c-0x2160]
			} else if c >= 0x24B0 && c <= 0x24EF {
				code = tables.Uni24b024ef[c-0x24B0]
			} else if c >= 0xFF20 && c <= 0xFF5F {
				code = tables.UniFf20Ff5f[c-0xFF20]
			}
			filename += string(code/80 + 0x30)
			filename += string(code%80 + 0x30)
			continue
		}

		filename += fmt.Sprintf("%04x", c)
	}
	return filename
}
