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

package constant

// AddonOperation addon 操作类别
type AddonOperation string

// addon 操作
const (
	InstallAddonOP   AddonOperation = "installAddon"
	UninstallAddonOP AddonOperation = "uninstallAddon"
	UpgradeAddonOP   AddonOperation = "upgradeAddon"
)

// addon 类型
const (
	Surreal = "surrealdb"
	VM      = "victoriametrics"
	RW      = "risingwave"
	GT      = "greptimedb"
	MILVUS  = "milvus"
)

// VM 组件定义
const (
	VMStorage string = "vmstorage"
	VMSelect  string = "vmselect"
	VMInsert  string = "vminsert"
)

const (
	VMClusterTopo string = "cluster"
	VMQueryTopo   string = "select"
)

// Surreal 组件定义
const (
	SurrealDB   string = "surreal"
	SurrealTikv string = "tikv"
	SurrealPd   string = "pd"
)
