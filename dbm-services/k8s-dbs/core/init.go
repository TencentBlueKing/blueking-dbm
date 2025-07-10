/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package core

import (
	"k8s-dbs/core/helper"
	"log"
	"log/slog"
)

// Init 集群管理核心服务初始化
func Init() error {
	if err := InitDB(); err != nil {
		return err
	}
	return nil
}

// InitDB 集群管理核心服务元数据初始化
func InitDB() error {
	log.Println("Start to initial MySql Connection...")
	if err := helper.Db.Init(); err != nil {
		slog.Error("Failed to initial MySql Connection", "error", err)
		return err
	}
	log.Println("Finish initialize MySql Connection...")
	return nil
}
