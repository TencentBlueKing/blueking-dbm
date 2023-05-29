//go:build windows
// +build windows

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
	"dbm-services/common/go-pubpkg/logger"
	"fmt"

	"golang.org/x/sys/windows/registry"
)

// WINSRegItem 定义window注册表的结构体
type WINSRegItem struct {
	ItemRootKey registry.Key
}

// ReadIiem 读取注册表项是否存在某个key
func (i *WINSRegItem) ReadIiem(ItemKeyPath string, ItemName string) (error, string) {
	// 读取注册表项,能读取成功则证明存在
	key, err := registry.OpenKey(i.ItemRootKey, ItemKeyPath, registry.READ)
	if err != nil {
		return err, ""
	}
	defer key.Close()
	value, _, err := key.GetStringValue(ItemName)
	if err != nil {
		return err, ""
	}

	return nil, value
}

// SetItem 注册表项下某个key的value
func (i *WINSRegItem) SetItem(ItemKeyPath string, ItemName string, SetVaule string) error {
	// 读取注册表项
	key, err := registry.OpenKey(i.ItemRootKey, ItemKeyPath, registry.SET_VALUE)
	if err != nil {
		return err
	}
	defer key.Close()
	err = key.SetStringValue(ItemName, SetVaule)
	if err != nil {
		return err
	}
	logger.Info(fmt.Sprintf("the reg key [%s\\%s\\%s] Set: [%s] successfully", i.ItemRootKey, ItemKeyPath, ItemName,
		SetVaule))
	return nil
}

// RemoveItem 删除注册表项
func (i *WINSRegItem) RemoveItem(ItemKeyPath string) error {
	// 读取注册表项
	err := registry.DeleteKey(i.ItemRootKey, ItemKeyPath)
	if err != nil {
		return err
	}
	logger.Info(fmt.Sprintf("the reg key [%s\\%s] delete successfully", i.ItemRootKey, ItemKeyPath))
	return nil
}
