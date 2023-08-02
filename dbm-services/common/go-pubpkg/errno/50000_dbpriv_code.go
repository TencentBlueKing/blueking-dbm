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
	// dbpriv code start  50000
	// GrantPrivilegesFail TODO
	GrantPrivilegesFail = Errno{Code: 51009, Message: "Grant Privileges Fail", CNMessage: "授权执行失败"}
	// GrantPrivilegesSuccess TODO
	GrantPrivilegesSuccess = Errno{Code: 0, Message: "Grant Privileges success", CNMessage: "授权执行成功"}
	// GrantPrivilegesParameterCheckFail TODO
	GrantPrivilegesParameterCheckFail = Errno{Code: 51010, Message: "Parameter of Grant Privileges Check Fail",
		CNMessage: "授权单据的参数检查失败"}
	// AccountRuleExisted TODO
	AccountRuleExisted = Errno{Code: 51001, Message: "Account rule of user on this db is existed ",
		CNMessage: "用户对此DB授权的账号规则已存在"}
	// AccountExisted TODO
	AccountExisted = Errno{Code: 51002, Message: "Account is existed ", CNMessage: "账号已存在"}
	// AccountNotExisted TODO
	AccountNotExisted = Errno{Code: 51003, Message: "Account not existed ", CNMessage: "账号不存在"}
	// PasswordConsistentWithAccountName TODO
	PasswordConsistentWithAccountName = Errno{Code: 51019, Message: "Password should be different from account name ",
		CNMessage: "账号与密码不能相同"}
	// PasswordOrAccountNameNull TODO
	PasswordOrAccountNameNull = Errno{Code: 51020, Message: "Password or account name should not be empty ",
		CNMessage: "账号与密码不能为空"}
	// AccountIdNull TODO
	AccountIdNull = Errno{Code: 51021, Message: "Account ID should not be empty",
		CNMessage: "账号ID不能为空"}
	// DbNameNull TODO
	DbNameNull = Errno{Code: 51022, Message: "Database name should not be empty",
		CNMessage: "数据库名称不能为空"}
	// AccountRuleIdNull TODO
	AccountRuleIdNull = Errno{Code: 51022, Message: "Account rule should not be empty",
		CNMessage: "账号规则ID不能为空"}
	// PrivNull TODO
	PrivNull = Errno{Code: 51022, Message: "No privilege was chosen", CNMessage: "未选择权限"}
	// AccountRuleNotExisted TODO
	AccountRuleNotExisted = Errno{Code: 51004, Message: "Account rule not existed ", CNMessage: "账号规则不存在"}
	// OnlyOneDatabaseAllowed TODO
	OnlyOneDatabaseAllowed = Errno{Code: 51005,
		Message:   "Only one database allowed, database name should not contain space",
		CNMessage: "只允许填写一个数据库，数据库名称不能包含空格"}
	// GenerateEncryptedPasswordErr TODO
	GenerateEncryptedPasswordErr = Errno{Code: 51007, Message: "Generate Encrypted Password Err",
		CNMessage: "创建账号，生成加密的密码时发生错误"}
	// ClonePrivilegesFail TODO
	ClonePrivilegesFail = Errno{Code: 51013, Message: "Clone privileges fail", CNMessage: "克隆权限失败"}
	// ClonePrivilegesCheckFail TODO
	ClonePrivilegesCheckFail = Errno{Code: 51014, Message: "Clone privileges check fail", CNMessage: "克隆权限检查失败"}
	// NoPrivilegesNothingToDo TODO
	NoPrivilegesNothingToDo = Errno{Code: 51015, Message: "no privileges,nothing to do", CNMessage: "没有权限需要克隆"}
	// CloudIdRequired TODO
	CloudIdRequired = Errno{Code: 51019, Message: "bk_cloud_id is required", CNMessage: "bk_cloud_id不能为空"}
	// ClusterTypeIsEmpty TODO
	ClusterTypeIsEmpty = Errno{Code: 51021, Message: "Cluster type can't be empty",
		CNMessage: "cluster type不能为空"}
	ModifyUserPasswordFail = Errno{Code: 51022, Message: "modify user password fail",
		CNMessage: "修改用户密码失败"}
	IncludeCharTypesLargerThanLength = Errno{Code: 51023, Message: "include char types larger than length",
		CNMessage: "要求包含的字符类型大于字符串长度"}
	TryTooManyTimes = Errno{Code: 51024, Message: "try too many times", CNMessage: "尝试太多次"}
	RuleIdNull      = Errno{Code: 51025, Message: "Rule ID should not be empty",
		CNMessage: "安全规则的id不能为空"}
	RuleNameNull = Errno{Code: 51026, Message: "Rule name should not be empty",
		CNMessage: "安全规则的名称不能为空"}
	RuleExisted       = Errno{Code: 51027, Message: "Rule already existed ", CNMessage: "规则已存在"}
	RuleNotExisted    = Errno{Code: 51028, Message: "Rule not existed ", CNMessage: "规则不存在"}
	NotMeetComplexity = Errno{Code: 51030, Message: "Set Passwords must meet complexity requirements",
		CNMessage: "设置的密码应该符合密码复杂度"}
	NameNull = Errno{Code: 51031, Message: "username should not be empty ",
		CNMessage: "用户名名称不能为空"}
)
