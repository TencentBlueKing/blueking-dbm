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

import (
	"k8s-dbs/i18n"

	goi18n "github.com/nicksnyder/go-i18n/v2/i18n"
)

// K8sDbsError Error
type K8sDbsError struct {
	Code        ErrorCode `json:"code"`        // Service Code
	MessageKey  string    `json:"-"`           // i18n message key (not serialized)
	Message     string    `json:"message"`     // Text information corresponding to the src code
	ErrorDetail string    `json:"errorDetail"` // Detailed error message
}

// Error string of error
func (e *K8sDbsError) Error() string {
	return e.ErrorDetail
}

// Localize 使用 localizer 本地化错误消息
func (e *K8sDbsError) Localize(localizer *goi18n.Localizer) *K8sDbsError {
	if localizer == nil || e.MessageKey == "" {
		return e
	}
	return &K8sDbsError{
		Code:        e.Code,
		MessageKey:  e.MessageKey,
		Message:     i18n.Translate(localizer, e.MessageKey),
		ErrorDetail: e.ErrorDetail,
	}
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
	OperationForbidden
	NotPermissionError
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
	InstallHelmChartErr
)

// addon 管理操作异常
const (
	InstallAddonError ErrorCode = iota + 1532400
	UninstallAddonError
	UpgradeAddonError
)

// errorCodeInfo 错误码信息结构体
type errorCodeInfo struct {
	MessageKey     string // i18n 消息 key
	DefaultMessage string // 默认消息（中文）
}

// codeInfoMap 错误码到 i18n key 和默认消息的映射
var codeInfoMap = map[ErrorCode]errorCodeInfo{
	// 纳管系统内置异常
	AuthError:             {i18n.MsgErrAuth, "权限不足，请联系管理员"},
	ServerError:           {i18n.MsgErrServer, "内部服务器出现错误"},
	EngineTypeError:       {i18n.MsgErrEngineType, "数据库引擎类型有误"},
	AuthorizationError:    {i18n.MsgErrAuthorization, "签名信息有误"},
	ThirdAPIError:         {i18n.MsgErrThirdAPI, "调用第三方 API 接口失败"},
	ResubmitError:         {i18n.MsgErrResubmit, "请勿重复提交"},
	LoginError:            {i18n.MsgErrLogin, "登录失败"},
	LogoutError:           {i18n.MsgErrLogout, "注销失败"},
	CreateMetaDataError:   {i18n.MsgErrCreateMetadata, "创建元数据失败"},
	UpdateMetaDataError:   {i18n.MsgErrUpdateMetadata, "更新元数据失败"},
	GetMetaDataError:      {i18n.MsgErrGetMetadata, "获取元数据失败"},
	DeleteMetaDataError:   {i18n.MsgErrDeleteMetadata, "删除元数据失败"},
	ParameterInvalidError: {i18n.MsgErrParameterInvalid, "参数校验失败"},
	ParameterTypeError:    {i18n.MsgErrParameterType, "参数类型校验失败"},
	ParameterValueError:   {i18n.MsgErrParameterValue, "参数值校验失败"},
	OperationForbidden:    {i18n.MsgErrOperationForbid, "禁止执行该操作"},
	NotPermissionError:    {i18n.MsgErrNotPermission, "权限不足"},

	// 存储集群操作异常
	DescribeClusterError:      {i18n.MsgErrClusterDescribe, "查询集群失败"},
	CreateClusterError:        {i18n.MsgErrClusterCreate, "创建集群失败"},
	GetClusterError:           {i18n.MsgErrClusterGet, "获取集群失败"},
	DeleteClusterError:        {i18n.MsgErrClusterDelete, "删除集群失败"},
	GetClusterStatusError:     {i18n.MsgErrClusterGetStatus, "查询集群状态失败"},
	GetClusterEventError:      {i18n.MsgErrClusterGetEvent, "查询集群事件失败"},
	VerticalScalingError:      {i18n.MsgErrClusterVerticalScale, "集群垂直扩缩容失败"},
	HorizontalScalingError:    {i18n.MsgErrClusterHorizScale, "集群水平扩缩容失败"},
	StartClusterError:         {i18n.MsgErrClusterStart, "集群启动失败"},
	StopClusterError:          {i18n.MsgErrClusterStop, "集群停止失败"},
	RestartClusterError:       {i18n.MsgErrClusterRestart, "集群重启失败"},
	UpgradeClusterError:       {i18n.MsgErrClusterUpgrade, "集群升级失败"},
	VolumeExpansionError:      {i18n.MsgErrClusterVolumeExpand, "集群磁盘扩缩容失败"},
	ExposeClusterError:        {i18n.MsgErrClusterExpose, "集群暴露服务失败"},
	DescribeOpsRequestError:   {i18n.MsgErrClusterDescribeOps, "查询操作请求失败"},
	GetOpsRequestStatusError:  {i18n.MsgErrClusterGetOpsStatus, "查询操作请求状态失败"},
	UpdateClusterError:        {i18n.MsgErrClusterUpdate, "更新集群失败"},
	PartialUpdateClusterError: {i18n.MsgErrClusterPartialUpdate, "局部更新集群失败"},
	GetClusterSvcError:        {i18n.MsgErrClusterGetSvc, "获取集群连接失败"},

	// k8s api server 调用异常
	CreateK8sNsError:         {i18n.MsgErrK8sCreateNs, "创建命名空间失败"},
	DeleteK8sNsError:         {i18n.MsgErrK8sDeleteNs, "删除命名空间失败"},
	GetPodLogError:           {i18n.MsgErrK8sGetPodLog, "获取 Pod 日志失败"},
	K8sAPIServerTimeoutError: {i18n.MsgErrK8sAPITimeout, "K8s API Server 请求超时"},
	GetPodDetailError:        {i18n.MsgErrK8sGetPodDetail, "获取 Pod 详情失败"},
	CreateK8sClientError:     {i18n.MsgErrK8sCreateClient, "获取 K8s Client 失败"},
	DeleteK8sPodError:        {i18n.MsgErrK8sDeletePod, "删除实例节点失败"},
	InstallHelmChartErr:      {i18n.MsgErrK8sInstallHelm, "安装 Helm chart 失败"},

	// 存储插件部署操作异常
	InstallAddonError:   {i18n.MsgErrAddonInstall, "插件安装失败"},
	UninstallAddonError: {i18n.MsgErrAddonUninstall, "插件卸载失败"},
	UpgradeAddonError:   {i18n.MsgErrAddonUpgrade, "插件更新失败"},

	// 组件操作异常
	DescribeComponentError: {i18n.MsgErrComponentDescribe, "查询组件失败"},
	GetComponentSvcError:   {i18n.MsgErrComponentGetSvc, "查询组件服务信息失败"},
	GetComponentPodsError:  {i18n.MsgErrComponentGetPods, "查询组件实例列表失败"},
}

// getCodeInfo 根据错误码获取错误信息
func getCodeInfo(code ErrorCode) errorCodeInfo {
	if info, ok := codeInfoMap[code]; ok {
		return info
	}
	return errorCodeInfo{MessageKey: "", DefaultMessage: "未知错误"}
}

// NewK8sDbsError 自定义错误
func NewK8sDbsError(code ErrorCode, err error) error {
	info := getCodeInfo(code)
	errorDetail := info.DefaultMessage
	if err != nil {
		errorDetail = err.Error()
	}

	return &K8sDbsError{
		Code:        code,
		MessageKey:  info.MessageKey,
		Message:     info.DefaultMessage,
		ErrorDetail: errorDetail,
	}
}

// NewK8sDbsErrorWithLocalizer 创建支持 i18n 的错误
func NewK8sDbsErrorWithLocalizer(code ErrorCode, err error, localizer *goi18n.Localizer) error {
	info := getCodeInfo(code)
	errorDetail := info.DefaultMessage
	if err != nil {
		errorDetail = err.Error()
	}

	message := info.DefaultMessage
	if localizer != nil && info.MessageKey != "" {
		message = i18n.Translate(localizer, info.MessageKey)
	}

	return &K8sDbsError{
		Code:        code,
		MessageKey:  info.MessageKey,
		Message:     message,
		ErrorDetail: errorDetail,
	}
}

// GetMessageKey 获取错误码对应的 i18n 消息 Key
func GetMessageKey(code ErrorCode) string {
	return getCodeInfo(code).MessageKey
}

// GetDefaultMessage 获取错误码对应的默认消息
func GetDefaultMessage(code ErrorCode) string {
	return getCodeInfo(code).DefaultMessage
}
