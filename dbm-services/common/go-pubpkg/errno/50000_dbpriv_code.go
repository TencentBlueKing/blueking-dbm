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

	// PasswordNotConsistent TODO
	PasswordNotConsistent = Errno{Code: 51008,
		Message:   "user is exist,but the new password is not consistent with the old password, should be consistent",
		CNMessage: "账号已存在，但是新密码与旧密码不一致，需要保持一致"}
	// GrantPrivilegesFail TODO
	GrantPrivilegesFail = Errno{Code: 51009, Message: "Grant Privileges Fail", CNMessage: "授权执行失败"}
	// GrantPrivilegesSuccess TODO
	GrantPrivilegesSuccess = Errno{Code: 0, Message: "Grant Privileges success", CNMessage: "授权执行成功"}
	// GrantPrivilegesParameterCheckFail TODO
	GrantPrivilegesParameterCheckFail = Errno{Code: 51010, Message: "Parameter of Grant Privileges Check Fail",
		CNMessage: "授权单据的参数检查失败"}
	// ErrPswNotIdentical TODO
	ErrPswNotIdentical = Errno{Code: 51000,
		Message: "Password is not identical to the password of existed account rules, " +
			"same accounts should use same password.",
		CNMessage: "密码与已存在的账号规则中的密码不同,相同账号的密码需要保持一致！"}
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
		Message: "Only one database allowed, database name should not contain space", CNMessage: "只允许填写一个数据库，数据库名称不能包含空格"}
	// ErrMysqlInstanceStruct TODO
	ErrMysqlInstanceStruct = Errno{Code: 51006, Message: "Not either tendbha or orphan structure",
		CNMessage: "不符合tendbha或者orphan的集群结构"}
	// GenerateEncryptedPasswordErr TODO
	GenerateEncryptedPasswordErr = Errno{Code: 51007, Message: "Generate Encrypted Password Err",
		CNMessage: "创建账号，生成加密的密码时发生错误"}
	// BkBizIdIsEmpty TODO
	BkBizIdIsEmpty = Errno{Code: 51012, Message: "bk_biz_id can't be empty", CNMessage: "bk_biz_id不能为空"}
	// ClonePrivilegesFail TODO
	ClonePrivilegesFail = Errno{Code: 51013, Message: "Clone privileges fail", CNMessage: "克隆权限失败"}
	// ClonePrivilegesCheckFail TODO
	ClonePrivilegesCheckFail = Errno{Code: 51014, Message: "Clone privileges check fail", CNMessage: "克隆权限检查失败"}
	// NoPrivilegesNothingToDo TODO
	NoPrivilegesNothingToDo = Errno{Code: 51015, Message: "no privileges,nothing to do", CNMessage: "没有权限需要克隆"}
	// DomainNotExists TODO
	DomainNotExists = Errno{Code: 51016, Message: "domain not exists", CNMessage: "域名不存在"}
	// IpPortFormatError TODO
	IpPortFormatError = Errno{Code: 51017, Message: "format not in 'ip:port' format",
		CNMessage: "格式不是ip:port的格式"}
	// InstanceNotExists TODO
	InstanceNotExists = Errno{Code: 51018, Message: "instance not exists", CNMessage: "实例不存在"}
	// CloudIdRequired TODO
	CloudIdRequired = Errno{Code: 51019, Message: "bk_cloud_id is required", CNMessage: "bk_cloud_id不能为空"}
	// NotSupportedClusterType TODO
	NotSupportedClusterType = Errno{Code: 51020, Message: "not supported cluster type", CNMessage: "不支持此集群类型"}
	// ClusterTypeIsEmpty TODO
	ClusterTypeIsEmpty = Errno{Code: 51021, Message: "Cluster type can't be empty", CNMessage: "cluster type不能为空"}
)
