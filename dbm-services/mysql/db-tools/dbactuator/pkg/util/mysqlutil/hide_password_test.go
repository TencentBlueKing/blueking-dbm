/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlutil_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

func TestClearSensitiveInformatio(t *testing.T) {
	t.Log("start ...")
	textString := "mysqldump  \t\t-h1.1.1.1  \t\t-P26000  \t\t-uxasasda  \t\t-p{xasx}  \t\t--skip-opt  \t\t--create-options   \t"
	t.Log(mysqlutil.ClearSensitiveInformation(textString))
}
