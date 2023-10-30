/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package osutil

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
)

// WINSOSUser 定义windows用户的结构体
type WINSOSUser struct {
	User    string
	Pass    string
	Comment string
}

// UserExists 定义判断windows系统用户是否存在的方法
func (w *WINSOSUser) UserExists() bool {

	output, err := StandardPowerShellCommand(
		fmt.Sprintf("(Get-WmiObject -Class Win32_UserAccount -Filter \"Name='%s'\").Name", w.User),
	)
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	if strings.TrimSpace(string(output)) == w.User {
		return true
	} else {
		return false
	}
}

// AddGroupMember TODO
// AddGroups 定义用户添加某个用户组
func (w *WINSOSUser) AddGroupMember(groupName string) error {

	// 判断用户是否在该组
	if w.IsExistInGroup(groupName) {
		logger.Info("The user [%s] in this group [%s], skip", w.User, groupName)
		return nil
	}
	_, err := StandardPowerShellCommand(
		fmt.Sprintf("Add-LocalGroupMember -Group '%s' -Member '%s'", groupName, w.User),
	)
	if err != nil {
		return err
	}
	logger.Info(fmt.Sprintf("Add system user [%s] in group [%s] successfully", w.User, groupName))
	return nil
}

// RemoveGroupMember 定义用户移除出某个用户组
func (w *WINSOSUser) RemoveGroupMember(groupName string) error {

	// 判断用户是否在该组
	if !w.IsExistInGroup(groupName) {
		logger.Info("The user [%s] not in this group [%s], skip", w.User, groupName)
		return nil
	}
	_, err := StandardPowerShellCommand(
		fmt.Sprintf("Remove-LocalGroupMember -Group '%s' -Member '%s'", groupName, w.User),
	)
	if err != nil {
		return err
	}
	logger.Info(fmt.Sprintf("Add system user [%s] has successfully removed the group [%s]", w.User, groupName))
	return nil
}

// CreateUser 定义创建系统用户的方法
func (w *WINSOSUser) CreateUser(isTranAdmin bool) error {
	// 创建账号，账号默认在内置的Users组

	_, err := StandardPowerShellCommand(
		fmt.Sprintf(
			"New-LocalUser -Name '%s' -Password (ConvertTo-SecureString '%s' -AsPlainText -Force) -Description '%s'",
			w.User, w.Pass, w.Comment),
	)
	if err != nil {
		return err
	}
	logger.Info(fmt.Sprintf("Create system user [%s] successfully", w.User))
	if isTranAdmin {
		// 判断加入系统内置管理组
		err := w.AddGroupMember("Administrators")
		if err != nil {
			return err
		}
	}
	return nil
}

// DropUser 定义删除系统用户的方法
func (w *WINSOSUser) DropUser() error {
	// 创建账号，账号不存在默认不报错

	_, err := StandardPowerShellCommand(
		fmt.Sprintf("Remove-LocalUser -Name '%s' -ErrorAction SilentlyContinue", w.User),
	)
	if err != nil {
		return err
	}

	logger.Info(fmt.Sprintf("drop system user [%s] successfully", w.User))

	return nil
}

// SetUerPass 定义设置系统用户的密码的方法
func (w *WINSOSUser) SetUerPass() error {
	// 创建账号，账号不存在默认不报错

	_, err := StandardPowerShellCommand(
		fmt.Sprintf(
			"Set-LocalUser -Name '%s' -Password (ConvertTo-SecureString '%s' -AsPlainText -Force) ",
			w.User,
			w.Pass,
		),
	)
	if err != nil {
		return err
	}

	logger.Info(fmt.Sprintf("System user [%s]set password successfully ", w.User))
	return nil
}

// IsExistInGroup 判断用户是否在某个用户组的方法
func (w *WINSOSUser) IsExistInGroup(groupName string) bool {
	output, err := StandardPowerShellCommand(
		fmt.Sprintf(
			"(Get-LocalGroupMember -group %s | Where-Object { $_.Name -like '*\\%s' -and $_.ObjectClass -eq 'User'}).Name",
			groupName, w.User),
	)
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	if string(output) != "" {
		return true
	} else {
		return false
	}
}
