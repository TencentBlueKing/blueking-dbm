// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package dbareport

import (
	"fmt"
	"path/filepath"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
)

func reportGrants(privFilePath string, reportDir string, port int) error {
	// 直接覆盖或者 rm 后再 copy，可能会日志采集不了
	filesRemove := filepath.Join(reportDir, "grants_report*.priv")
	cmutil.RemoveFileMatch(filesRemove, true)
	reportFile := filepath.Join(reportDir, fmt.Sprintf("grants_report_%d_%d.priv", port, time.Now().Weekday()))
	return cmutil.OSCopyFile(privFilePath, reportFile)
}
