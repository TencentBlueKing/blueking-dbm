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

package errors

// K8sDbsError Error
type K8sDbsError struct {
	Code             int    `json:"code"`    // Service Code
	Message          string `json:"message"` // Text information corresponding to the src code
	RealErrorMessage string `json:"err_msg"`
}

// Error string of error
func (e *K8sDbsError) Error() string {
	return e.Message
}

// 通用内部业务逻辑异常
const (
	ServerError        = 1532101
	EngineTypeError    = 1532102
	AuthorizationError = 1532103
	CallHTTPError      = 1532104
	ResubmitMsg        = 1532105
	AuthErr            = 1532106
	LoginErr           = 1532107
	LogoutErr          = 1532108
	CreateMetaDataErr  = 1532109
	UpdateMetaDataErr  = 1532110
	GetMetaDataErr     = 1532111
	DeleteMetaDataErr  = 1532112
)

// 存储集群 cluster 操作异常
const (
	DescribeClusterError      = 1532201
	CreateClusterError        = 1532202
	DeleteClusterError        = 1532203
	GetClusterStatusError     = 1532204
	VerticalScalingError      = 1532205
	HorizontalScalingError    = 1532206
	StartClusterError         = 1532207
	StopClusterError          = 1532208
	RestartClusterError       = 1532209
	UpgradeClusterError       = 1532210
	VolumeExpansionError      = 1532211
	ExposeClusterError        = 1532212
	DescribeOpsRequestError   = 1532213
	GetOpsRequestStatusError  = 1532214
	UpdateClusterError        = 1532215
	GetClusterEventError      = 1532216
	PartialUpdateClusterError = 1532217
	GetClusterSvcError        = 1532218
)

// 存储集群 component 操作异常
const (
	DescribeComponentError = 1532500
	GetComponentSvcError   = 1532501
)

// k8s 集群管理操作异常
const (
	CreateK8sNsError         = 1532300
	DeleteK8sNsError         = 1532301
	GetPodLogError           = 1532302
	K8sAPIServerTimeoutError = 1532303
)

// addon 管理操作异常
const (
	InstallAddonError   = 1532400
	UninstallAddonError = 1532401
	UpgradeAddonError   = 1532402
)

// 定义错误码对于的message
var codeTag = map[int]string{
	// 纳管系统内置异常
	AuthErr:            "权限不足，请联系管理员",
	ServerError:        "内部服务器出现错误",
	EngineTypeError:    "数据库引擎类型有误",
	AuthorizationError: "签名信息有误",
	CallHTTPError:      "调用第三方 HTTP 接口失败",
	ResubmitMsg:        "请勿重复提交",
	LoginErr:           "登录失败",
	LogoutErr:          "注销失败",
	CreateMetaDataErr:  "创建元数据失败",
	UpdateMetaDataErr:  "更新元数据失败",
	GetMetaDataErr:     "获取元数据失败",
	DeleteMetaDataErr:  "删除元数据失败",

	// 存储集群操作异常
	DescribeClusterError:      "查询集群失败",
	CreateClusterError:        "创建集群失败",
	DeleteClusterError:        "删除集群失败",
	GetClusterStatusError:     "查询集群状态失败",
	GetClusterEventError:      "查询集群事件失败",
	VerticalScalingError:      "集群水平扩缩容失败",
	HorizontalScalingError:    "集群垂直扩缩容失败",
	StartClusterError:         "集群启动失败",
	StopClusterError:          "集群停止失败",
	RestartClusterError:       "集群重启失败",
	UpgradeClusterError:       "集群升级失败",
	VolumeExpansionError:      "集群磁盘扩容失败",
	ExposeClusterError:        "集群暴露服务失败",
	DescribeOpsRequestError:   "查询操作请求失败",
	GetOpsRequestStatusError:  "查询操作请求状态失败",
	UpdateClusterError:        "更新集群失败",
	PartialUpdateClusterError: "局部更新集群失败",
	GetClusterSvcError:        "获取集群连接失败",

	// k8s api server 调用异常
	CreateK8sNsError:         "创建命名空间失败",
	DeleteK8sNsError:         "删除命名空间失败",
	GetPodLogError:           "获取 Pod 日志失败",
	K8sAPIServerTimeoutError: "K8s API Server 请求超时",

	// 存储插件部署操作异常
	InstallAddonError:   "插件安装失败",
	UninstallAddonError: "插件卸载失败",
	UpgradeAddonError:   "插件更新失败",

	// 组件操作异常
	DescribeComponentError: "查询组件失败",
	GetComponentSvcError:   "查询组件服务信息失败",
}

// NewK8sDbsError 自定义错误
func NewK8sDbsError(code int, err error) error {
	return &K8sDbsError{
		Code:             code,
		Message:          codeTag[code],
		RealErrorMessage: err.Error(),
	}
}
