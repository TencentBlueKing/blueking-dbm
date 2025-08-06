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
	Code        ErrorCode `json:"code"`    // Service Code
	Message     string    `json:"message"` // Text information corresponding to the src code
	ErrorDetail string    `json:"errorDetail"`
}

// Error string of error
func (e *K8sDbsError) Error() string {
	return e.ErrorDetail
}

type ErrorCode int

// 通用内部业务逻辑异常
const (
	ServerError ErrorCode = iota + 1532101
	EngineTypeError
	AuthorizationError
	ThirdAPIError
	ResubmitError
	AuthError
	LoginError
	LogoutError
	CreateMetaDataError
	UpdateMetaDataError
	GetMetaDataError
	DeleteMetaDataError
	ParameterInvalidError
	ParameterTypeError
	ParameterValueError
	OperationFobidden
)

// 存储集群 cluster 操作异常
const (
	DescribeClusterError ErrorCode = iota + 1532201
	CreateClusterError
	DeleteClusterError
	GetClusterError
	GetClusterStatusError
	VerticalScalingError
	HorizontalScalingError
	StartClusterError
	StopClusterError
	RestartClusterError
	UpgradeClusterError
	VolumeExpansionError
	ExposeClusterError
	DescribeOpsRequestError
	GetOpsRequestStatusError
	UpdateClusterError
	GetClusterEventError
	PartialUpdateClusterError
	GetClusterSvcError
)

// 存储集群 component 操作异常
const (
	DescribeComponentError ErrorCode = iota + 1532500
	GetComponentSvcError
	GetComponentPodsError
)

// k8s 集群管理操作异常
const (
	CreateK8sNsError ErrorCode = iota + 1532300
	DeleteK8sNsError
	GetPodLogError
	K8sAPIServerTimeoutError
	GetPodDetailError
	CreateK8sClientError
	DeleteK8sPodError
)

// addon 管理操作异常
const (
	InstallAddonError ErrorCode = iota + 1532400
	UninstallAddonError
	UpgradeAddonError
)

// 定义错误码对于的message
var codeTag = map[ErrorCode]string{
	// 纳管系统内置异常
	AuthError:             "权限不足，请联系管理员",
	ServerError:           "内部服务器出现错误",
	EngineTypeError:       "数据库引擎类型有误",
	AuthorizationError:    "签名信息有误",
	ThirdAPIError:         "调用第三方 API 接口失败",
	ResubmitError:         "请勿重复提交",
	LoginError:            "登录失败",
	LogoutError:           "注销失败",
	CreateMetaDataError:   "创建元数据失败",
	UpdateMetaDataError:   "更新元数据失败",
	GetMetaDataError:      "获取元数据失败",
	DeleteMetaDataError:   "删除元数据失败",
	ParameterInvalidError: "参数校验失败",
	ParameterTypeError:    "参数类型校验失败",
	ParameterValueError:   "参数值校验失败",
	OperationFobidden:     "禁止执行该操作",

	// 存储集群操作异常
	DescribeClusterError:      "查询集群失败",
	CreateClusterError:        "创建集群失败",
	GetClusterError:           "获取集群失败",
	DeleteClusterError:        "删除集群失败",
	GetClusterStatusError:     "查询集群状态失败",
	GetClusterEventError:      "查询集群事件失败",
	VerticalScalingError:      "集群垂直扩缩容失败",
	HorizontalScalingError:    "集群水平扩缩容失败",
	StartClusterError:         "集群启动失败",
	StopClusterError:          "集群停止失败",
	RestartClusterError:       "集群重启失败",
	UpgradeClusterError:       "集群升级失败",
	VolumeExpansionError:      "集群磁盘扩缩容失败",
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
	GetPodDetailError:        "获取 Pod 详情失败",
	CreateK8sClientError:     "获取 K8s Client 失败",
	DeleteK8sPodError:        "删除实例节点失败",

	// 存储插件部署操作异常
	InstallAddonError:   "插件安装失败",
	UninstallAddonError: "插件卸载失败",
	UpgradeAddonError:   "插件更新失败",

	// 组件操作异常
	DescribeComponentError: "查询组件失败",
	GetComponentSvcError:   "查询组件服务信息失败",
	GetComponentPodsError:  "查询组件实例列表失败",
}

// NewK8sDbsError 自定义错误
func NewK8sDbsError(code ErrorCode, err error) error {
	return &K8sDbsError{
		Code:        code,
		Message:     codeTag[code],
		ErrorDetail: err.Error(),
	}
}
