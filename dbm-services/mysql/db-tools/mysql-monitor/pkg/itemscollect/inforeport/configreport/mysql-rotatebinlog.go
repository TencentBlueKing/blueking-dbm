// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package configreport

import (
	"path/filepath"

	actorCst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
)

// ReportRotatebinlogConfig 上报 rotatebinlog 配置（目前按主机，不分端口）
func ReportRotatebinlogConfig(dbPort int) error {
	confFile := filepath.Join(actorCst.MysqlRotateBinlogInstallPath, "main.yaml")
	cnf, err := rotate.ReadMainConfig(confFile)
	if err != nil {
		return err
	}
	report, err := GetMixedReport("rotatebinlog_config_main.log")
	if err != nil {
		return err
	}
	event := NewDynamicEvent("rotatebinlog_config", "tendbha", 1)
	event.SetPayload(cnf)
	report.Println(event)
	return nil
}
