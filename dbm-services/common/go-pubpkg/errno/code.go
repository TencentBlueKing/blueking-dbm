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
	// ErrErrInvalidParam TODO
	ErrErrInvalidParam = Errno{Code: 10005, Message: "parameter validity check failed",
		CNMessage: "参数合法性检查不通过"}

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

	// ErrDBQuery TODO
	ErrDBQuery = Errno{Code: 10201, Message: "DB Query error.", CNMessage: "查询DB错误!"}
	// ErrModelFunction TODO
	ErrModelFunction = Err{Errno: Errno{Code: 10202, Message: "Error occured while invoking model function.",
		CNMessage: "调用 DB model 方法发生错误！"}, Err: nil}

	// ErrDoNotHavePrivs TODO
	ErrDoNotHavePrivs = Errno{Code: 10301, Message: "User don't have Privs.", CNMessage: "此用户没有权限"}
	// ErrUserIsEmpty TODO
	ErrUserIsEmpty = Errno{Code: 10302, Message: "User can't be empty.", CNMessage: "user 不能为空！"}

	// StartBiggerThanEndTime TODO
	StartBiggerThanEndTime = Errno{Code: 10060, Message: "Start time is bigger than end time.", CNMessage: "开始时间大于结束时间"}

	// RepeatedIpExistSystem TODO
	RepeatedIpExistSystem = Errno{Code: 10070, CNMessage: "存在重复IP", Message: "there is a duplicate ip"}

	// ErrInvokeAPI TODO
	ErrInvokeAPI = Errno{Code: 15000, Message: "Error occurred while invoking API", CNMessage: "调用 API 发生错误！"}

	// ErrRecordNotFound TODO
	ErrRecordNotFound = Errno{Code: 404, Message: "There is no records in db.", CNMessage: "数据库未找到对应的记录！"}

	// ErrValidation TODO
	ErrValidation = Errno{Code: 20001, Message: "Validation failed."}
	// ErrDatabase TODO
	ErrDatabase = Errno{Code: 20002, Message: "Database error."}
	// ErrToken TODO
	ErrToken = Errno{Code: 20003, Message: "Error occurred while signing the JSON web token."}

	// ErrEncrypt TODO
	// user errors
	ErrEncrypt = Errno{Code: 20101, Message: "Error occurred while encrypting the user password."}
	// ErrUserNotFound TODO
	ErrUserNotFound = Errno{Code: 20102, Message: "The user was not found."}
	// ErrTokenInvalid TODO
	ErrTokenInvalid = Errno{Code: 20103, Message: "The token was invalid."}
	// ErrPasswordIncorrect TODO
	ErrPasswordIncorrect = Errno{Code: 20104, Message: "The password was incorrect."}

	// BkBizIdIsEmpty TODO
	BkBizIdIsEmpty = Errno{Code: 51012, Message: "bk_biz_id can't be empty", CNMessage: "bk_biz_id不能为空"}
	// InstanceNotExists TODO
	InstanceNotExists = Errno{Code: 51018, Message: "instance not exists", CNMessage: "实例不存在"}
)
