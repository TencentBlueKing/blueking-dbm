/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package components

import (
	"fmt"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"
)

// Medium 通用介质包处理
type Medium struct {
	Pkg    string `json:"pkg" validate:"required"`          // 安装包名
	PkgMd5 string `json:"pkg_md5"  validate:"required,md5"` // 安装包MD5
}

// Check TODO
func (m *Medium) Check() (err error) {
	var fileMd5 string
	// 判断安装包是否存在
	pkgAbPath := m.GetAbsolutePath()
	if !util.FileExists(pkgAbPath) {
		return fmt.Errorf("%s不存在", pkgAbPath)
	}
	if fileMd5, err = util.GetFileMd5(pkgAbPath); err != nil {
		return fmt.Errorf("获取[%s]md5失败, %v", m.Pkg, err.Error())
	}
	// 校验md5
	if fileMd5 != m.PkgMd5 {
		return fmt.Errorf("安装包的md5不匹配,[%s]文件的md5[%s]不正确", fileMd5, m.PkgMd5)
	}
	return
}

// GetAbsolutePath 返回介质存放的绝对路径
func (m *Medium) GetAbsolutePath() string {
	return fmt.Sprintf("%s%s\\%s", cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME, m.Pkg)
}
