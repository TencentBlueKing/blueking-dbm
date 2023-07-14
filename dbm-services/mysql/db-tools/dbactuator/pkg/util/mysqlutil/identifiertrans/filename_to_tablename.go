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

func FilenameToTableName(filename string) (tablename string, err error) {
	for idx := 0; idx < len(filename); {
		if filename[idx] < 128 && tables.SafeChar[filename[idx]] {
			tablename += string(filename[idx])
			idx += 1
			continue
		}

		if filename[idx] != '@' {
			return "", fmt.Errorf("invalid char filename[%d]=%c", idx, filename[idx])
		}

		if idx+3 > len(filename) {
			return "", fmt.Errorf("invalid sequence filename[%d:]=%s", idx, filename[idx:])
		}

		c1 := filename[idx+1]
		c2 := filename[idx+2]

		if c1 >= 0x30 && c1 <= 0x7F && c2 >= 0x30 && c2 <= 0x7F {
			code := (int(c1)-0x30)*80 + int(c2) - 0x30
			if code < 5994 && tables.ToUni[code] > 0 {
				tablename += string(tables.ToUni[code])
				idx += 3
				continue
			}

			if c1 == '@' && c2 == '@' {
				tablename += string(rune(0))
				idx += 3
				continue
			}
		}

		if idx+4 > len(filename) {
			return "", fmt.Errorf("invalid sequence filename[%d:]=%s", idx, filename[idx:])
		}

		h1 := tables.HexLo(c1)
		h2 := tables.HexLo(c2)
		if h1 >= 0 && h2 >= 0 {
			h3 := tables.HexLo(filename[idx+3])
			h4 := tables.HexLo(filename[idx+4])
			if h3 >= 0 && h4 >= 0 {
				code := (h1 << 12) + (h2 << 8) + (h3 << 4) + h4
				tablename += string(rune(code))
				idx += 5
				continue
			}
		}
	}
	return tablename, nil
}
