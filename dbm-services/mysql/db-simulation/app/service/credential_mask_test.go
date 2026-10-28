/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import "testing"

func TestHideBasicAuthPassword(t *testing.T) {
	cmd := "curl -u repo-user:p@ss:w/rd  -s -S -o a.sql http://bkrepo/generic/p/b/a.sql"
	got := hideBasicAuthPassword(cmd, "repo-user", "p@ss:w/rd")
	if got != "curl -u repo-user:xxxx  -s -S -o a.sql http://bkrepo/generic/p/b/a.sql" {
		t.Fatalf("password not hidden: %s", got)
	}
	anonymous := "curl -s -S -o a.sql http://bkrepo/generic/p/b/a.sql"
	if got := hideBasicAuthPassword(anonymous, "", ""); got != anonymous {
		t.Fatalf("command without credential changed: %s", got)
	}
}
