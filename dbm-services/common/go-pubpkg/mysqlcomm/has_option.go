/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlcomm

import (
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
)

// MysqlbinlogHasOpt return nil if option exists
func MysqlbinlogHasOpt(binlogCmd string, option string) error {
	outStr, errStr, err := cmutil.ExecCommand(false, "", binlogCmd, "--help")
	if err != nil {
		return err
	}
	if strings.Contains(errStr, "unknown option") {
		return errors.Errorf("mysqlbinlog %s has no option %s", binlogCmd, option)
	}
	if strings.Contains(outStr, option) {
		return nil
	}
	return errors.Errorf("check option error for %s %s", binlogCmd, option)
}

// MysqldumpHasOption check mysqldump has --xxx or not
func MysqldumpHasOption(bin string, option string) (bool, error) {
	// 注意 --help 要在后面
	// spider-4 的 mysqldump --xxx --help 报错 错误码返回 0 !!
	cmdStdout, cmdStderr, err := cmutil.ExecCommand(false, "", bin, option, "--help")
	out := cmdStderr + cmdStdout
	// unknown variable
	if strings.Contains(out, "unknown option") || strings.Contains(out, "unknown variable") {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return true, nil
}

// MysqlCliHasOption test mysql client has option or not
func MysqlCliHasOption(mysqlCmd string, option string) error {
	outStr, errStr, err := cmutil.ExecCommand(false, "", mysqlCmd, "--help")
	out := errStr + outStr
	if strings.Contains(out, "unknown option") || strings.Contains(out, "unknown variable") {
		return errors.Errorf("mysql %s has no option %s", mysqlCmd, option)
	}
	if err != nil {
		return err
	}
	if strings.Contains(outStr, option) {
		return nil
	}
	return errors.Errorf("check option error for %s %s", mysqlCmd, option)
}

// MysqlAdminHasOption test mysqladmin has option or not
func MysqlAdminHasOption(mysqlCmd string, option string) (bool, error) {
	cmdStdout, cmdStderr, err := cmutil.ExecCommand(false, "", mysqlCmd, option, "--help")
	out := cmdStderr + cmdStdout
	//unknown option
	if strings.Contains(out, "unknown option") {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return true, nil
}
