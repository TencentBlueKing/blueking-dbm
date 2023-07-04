/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package errno

var (
	// OK TODO
	// Common errors
	// OK = Errno{Code: 0, Message: ""}
	OK = Errno{Code: 0, Message: "", CNMessage: ""}

	// InternalServerError TODO
	InternalServerError = Errno{Code: 10001, Message: "Internal server error", CNMessage: "服务器内部错误。"}
	// ErrBind TODO
	ErrBind = Errno{Code: 10002, Message: "Error occurred while binding the request body to the struct.",
		CNMessage: "请求参数发生错误。"}
	// ErrReadEntity TODO
	ErrReadEntity = Errno{Code: 10003, Message: "Error occurred while parsing the request parameter.",
		CNMessage: "Error occurred while parsing the request parameter."}
	// ErrJSONUnmarshal TODO
	ErrJSONUnmarshal = Errno{Code: 10004, Message: "Error occurred while Unmarshaling the JSON to data model.",
		CNMessage: "json反序列化失败"}
	// ErrInputParameter TODO
	ErrInputParameter = Errno{Code: 10005, Message: "input pramater error.", CNMessage: "输入参数错误"}

	// ErrBytesToMap TODO
	ErrBytesToMap = Errno{Code: 50307, Message: "Error occurred while converting bytes to map.",
		CNMessage: "Error occurred while converting bytes to map."}

	// ErrString2Int TODO
	ErrString2Int = Errno{Code: 10110, Message: "Error occurred while convert string to int."}
	// ErrGetJSONArray TODO
	ErrGetJSONArray = Errno{Code: 10111, Message: "Get simplejson Array error.", CNMessage: ""}
	// ErrConvert2Map TODO
	ErrConvert2Map = Errno{Code: 10112, Message: "Error occurred while converting the data to Map.",
		CNMessage: "Error occurred while converting the data to Map."}
	// ErrJSONMarshal TODO
	ErrJSONMarshal = Errno{Code: 10113, Message: "Error occurred while marshaling the data to JSON.",
		CNMessage: "json序列化失败"}
	// ErrTypeAssertion TODO
	ErrTypeAssertion = Errno{Code: 10114, Message: "Error occurred while doing type assertion.", CNMessage: "类型断言失败"}
	// ErrParameterRequired TODO
	ErrParameterRequired = Errno{Code: 10115, Message: "Input paramter required"}

	// ErrorJsonToMap TODO
	ErrorJsonToMap = Errno{Code: 10114, Message: "Error occured while converting json to Map.",
		CNMessage: "Json 转为 Map 出现错误！"}

	// [数据库类型错误] 10200 开始

	// ErrDBQuery TODO
	ErrDBQuery = Errno{Code: 10201, Message: "DB Query error.", CNMessage: "查询DB错误!"}
	// ErrModelFunction TODO
	ErrModelFunction = Err{Errno: Errno{Code: 10202, Message: "Error occured while invoking model function.",
		CNMessage: "调用 DB model 方法发生错误！"}, Err: nil}

	// [用户权限类错误] 10300 开始

	// ErrDoNotHavePrivs TODO
	ErrDoNotHavePrivs = Errno{Code: 10301, Message: "User don't have Privs.", CNMessage: "此用户没有权限"}
	// ErrUserIsEmpty TODO
	ErrUserIsEmpty = Errno{Code: 10302, Message: "User can't be empty.", CNMessage: "user 不能为空！"}

	// StartBiggerThanEndTime TODO
	StartBiggerThanEndTime = Errno{Code: 10060, Message: "Start time is bigger than end time.", CNMessage: "开始时间大于结束时间"}

	// RepeatedIpExistSystem TODO
	RepeatedIpExistSystem = Errno{Code: 10070, CNMessage: "存在重复IP", Message: "there is a duplicate ip"}

	// ErrInvokeAPI TODO
	// call other service error
	ErrInvokeAPI = Errno{Code: 15000, Message: "Error occurred while invoking API", CNMessage: "调用 API 发生错误！"}
)
