// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlconnlog

import (
	"time"
)

type connRecord struct {
	ConnId       int64     `db:"conn_id" json:"conn_id"`
	ConnTime     time.Time `db:"conn_time" json:"conn_time"`
	UserName     string    `db:"user_name" json:"user_name"`
	CurUserName  string    `db:"cur_user_name" json:"cur_user_name"`
	Ip           string    `db:"ip" json:"ip"`
	BkBizId      int       `json:"bk_biz_id"`
	BkCloudId    *int      `json:"bk_cloud_id"`
	ImmuteDomain string    `json:"immute_domain"`
	Port         int       `json:"port"`
	MachineType  string    `json:"machine_type"`
	Role         *string   `json:"role"`
}
