package errno

var (
	// OK TODO
	// Common errors
	// OK = Errno{Code: 0, Message: ""}
	OK = Errno{Code: 0, Message: "", CNMessage: ""}
	// SaveOK TODO
	SaveOK = Errno{Code: 0, Message: "Bill save success!", CNMessage: "单据保存成功!"}
	// CommitOK TODO
	CommitOK = Errno{Code: 0, Message: "Bill commit success!", CNMessage: "单据提交成功!"}
	// AuditOK TODO
	AuditOK = Errno{Code: 0, Message: "Bill audit success!", CNMessage: "单据审核成功!"}
	// RollbackOK TODO
	RollbackOK = Errno{Code: 0, Message: "Bill rollback success!", CNMessage: "单据驳回成功!"}
	// StopOK TODO
	StopOK = Errno{Code: 0, Message: "Bill stop success!", CNMessage: "单据终止成功!"}
	// ExecuteOK TODO
	ExecuteOK = Errno{Code: 0, Message: "Bill execute success!", CNMessage: "单据执行成功!"}
	// CommonOK TODO
	CommonOK = Errno{Code: 0, Message: "", CNMessage: "通用成功描述"}
	// JobUpdateOK TODO
	JobUpdateOK = Errno{Code: 0, Message: "Job update success!", CNMessage: "Job 更新成功!"}
	// SubjobUpdateOK TODO
	SubjobUpdateOK = Errno{Code: 0, Message: "Subjob update success!", CNMessage: "Subjob 更新成功!"}

	// ErrRecordNotFound TODO
	ErrRecordNotFound = Errno{Code: 404, Message: "There is no records in db.", CNMessage: "数据库未找到对应的记录！"}

	// CommonErr TODO
	CommonErr = Errno{Code: 10000, Message: "common error!", CNMessage: "通用错误!"}

	// InternalServerError TODO
	InternalServerError = Errno{Code: 10001, Message: "Internal server error", CNMessage: "服务器内部错误。"}
	// ErrBind TODO
	ErrBind = Errno{Code: 10002, Message: "Error occurred while binding the request body to the struct.",
		CNMessage: "参数处理发生错误。"}
	// ErrString2Int TODO
	ErrString2Int = Errno{Code: 10010, Message: "Error occurred while convert string to int.",
		CNMessage: "string 转化为 int 出错！"}
	// ErrorJsonToMap TODO
	ErrorJsonToMap = Errno{Code: 10030, Message: "Error occured while converting json to Map.",
		CNMessage: "Json 转为 Map 出现错误！"}
	// ErrorUIDBeZero TODO
	ErrorUIDBeZero = Errno{Code: 10035, Message: "uid can not be 0!", CNMessage: "uid 不能为 0.！"}
	// ErrRequestParam TODO
	ErrRequestParam = Errno{Code: 10036, Message: "request parameter error!", CNMessage: "请求参数错误！"}

	// ErrTypeAssertion TODO
	ErrTypeAssertion = Errno{Code: 10040, Message: "Error occurred while doing type assertion."}
	// ErrParameterRequired TODO
	ErrParameterRequired = Errno{Code: 10050, Message: "Input paramter required"}
	// StartBiggerThanEndTime TODO
	StartBiggerThanEndTime = Errno{Code: 10060, Message: "Start time is bigger than end time."}

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
	// ErrDoNotHavePrivs TODO
	ErrDoNotHavePrivs = Errno{Code: 20106, Message: "User don't have Privs."}
	// ErrUserIsEmpty TODO
	ErrUserIsEmpty = Errno{Code: 20110, Message: "User can't be empty.", CNMessage: "user 不能为空！"}
	// ErrAppNameIsEmpty TODO
	ErrAppNameIsEmpty = Errno{Code: 20115, Message: "App name can't be empty.", CNMessage: "业务名不能为空！"}

	// ErrCommonExecute TODO
	ErrCommonExecute = Errno{Code: 20200, Message: "Error occured while invoking execute method.",
		CNMessage: "调用 execute 出错！"}

	// ErrUserHaveNoProjectPriv TODO
	ErrUserHaveNoProjectPriv = Errno{Code: 30000, Message: "User don't have project priv.", CNMessage: "没有 project 权限！"}

	// ErrGcsBillNotFound TODO
	// gcsbill errors
	ErrGcsBillNotFound = Errno{Code: 40000, Message: "Gcs bill was not found.", CNMessage: "单据不存在！"}
	// ErrGCSBillTypeEmpty TODO
	ErrGCSBillTypeEmpty = Errno{Code: 40001, Message: "Gcs bill type can not be empty.", CNMessage: "单据类型不能为空！"}
	// InvalidGCSBillType TODO
	InvalidGCSBillType = Errno{Code: 40002, Message: "Invalid Gcs bill type.", CNMessage: "无效的 GCS 单据类型！"}
	// InvalidAuditLevel TODO
	InvalidAuditLevel = Errno{Code: 40003, Message: "Invalid Bill Audit level.", CNMessage: "无效的单据审核级别！"}

	// CannotGetBillStatus TODO
	CannotGetBillStatus = Errno{Code: 40004, Message: "Cann't get bill status.", CNMessage: `无法获取单据状态`}
	// ErrGCSBillnotAuditable TODO
	ErrGCSBillnotAuditable = Errno{Code: 40005, Message: "Current GCS bill is not in audit status now.",
		CNMessage: `当前单据不在“待审核”状态！`}
	// ErrGCSBillNotInExecute TODO
	ErrGCSBillNotInExecute = Errno{Code: 40006, Message: "Bill is not in execute status.", CNMessage: `当前单据不在“待执行”状态！`}
	// ErrGCSBillAudit TODO
	ErrGCSBillAudit = Errno{Code: 40007, Message: "Audit bill error.", CNMessage: `审核单据出错。`}

	// ErrNotHaveBillCommitPriv TODO
	ErrNotHaveBillCommitPriv = Errno{Code: 40008, Message: "user don't have bill commit priv", CNMessage: "用户没有提单权限！"}

	// ErrGetGCSDoneBills TODO
	ErrGetGCSDoneBills = Errno{Code: 40009, Message: "Error occured while getting done bills.",
		CNMessage: "获取个人已办事项出错！"}
	// ErrBillAppIsEmpty TODO
	ErrBillAppIsEmpty = Errno{Code: 40010, Message: "Gcs bill app can not be empty.", CNMessage: "单据的业务名不能为空！"}
	// ErrGCSBillNoExecutePriv TODO
	ErrGCSBillNoExecutePriv = Errno{Code: 40011, Message: "Only apply user and follower can execute the bill!",
		CNMessage: "只有申请人或者关注人可以执行单据！"}
	// ErrGetGCSBillModel TODO
	ErrGetGCSBillModel = Errno{Code: 40012, Message: "Error occured while getting bill info",
		CNMessage: "获取 Bill 详情出错"}
	// ErrGetGCSBillTypes TODO
	ErrGetGCSBillTypes = Errno{Code: 40014, Message: "Error occured while getting bill types",
		CNMessage: "获取所有单据类型失败！"}
	// ErrGCSBillCommit TODO
	ErrGCSBillCommit = Err{Errno: Errno{Code: 40015, Message: "The bill can not be committed repeatly!",
		CNMessage: "单据不能被重复提交！"}}
	// ErrInvokeBillCommit TODO
	ErrInvokeBillCommit = Err{Errno: Errno{Code: 40016, Message: "Error occured while committing gcs bills",
		CNMessage: "单据提交时发生错误！"}}
	// ErrInvokeBillExecute TODO
	ErrInvokeBillExecute = Err{Errno: Errno{Code: 40017, Message: "Error occured while executing gcs bills",
		CNMessage: "单据执行时发生错误！"}}

	// ErrGCSBillnotRollback TODO
	ErrGCSBillnotRollback = Errno{Code: 40019, Message: "Bill is not auditable ,it can not be rollback.",
		CNMessage: `非“待审核”单据不能被驳回！`}
	// ErrGetGCSBills TODO
	ErrGetGCSBills = Errno{Code: 40020, Message: "Error occured while getting gcs bills", CNMessage: "获取单据失败！"}
	// ErrCloneUnfinishedBills TODO
	ErrCloneUnfinishedBills = Errno{Code: 40022, Message: "Error occured while cloning unfinished gcs bills",
		CNMessage: "不能克隆没有结束的单据！"}
	// ErrFinishedBills TODO
	ErrFinishedBills = Errno{Code: 40027, Message: "Error occured while finishing gcs bills",
		CNMessage: `设置单据为“完成”状态时失败！`}
	// ErrBillHaveTerminated TODO
	ErrBillHaveTerminated = Errno{Code: 40028, Message: "Bill have terminated!", CNMessage: `单据已“终止”！`}

	// ErrNoStopPriv TODO
	ErrNoStopPriv = Errno{Code: 40037, Message: "Don't have stop bill priv!", CNMessage: `用户没有“终止”单据权限！`}
	// ErrGCSBillSave TODO
	ErrGCSBillSave = Err{Errno: Errno{Code: 40042, Message: "Error occured while saving gcs bills!",
		CNMessage: "单据保存失败！"}}
	// ErrBillIsNotUncommit TODO
	ErrBillIsNotUncommit = Err{Errno: Errno{Code: 40043,
		Message: "Bill phase is not v_uncommit before committing the bill!", CNMessage: "单据提交之前，单据状态不是\"未提交\"！"}}
	// ErrBillPreCommit TODO
	ErrBillPreCommit = Err{Errno: Errno{Code: 40046, Message: "Error occured while invoking bill pre commit api:",
		CNMessage: "调用单据的 PreCommit API 失败:"}}
	// ErrBillAfterExecute TODO
	ErrBillAfterExecute = Err{Errno: Errno{Code: 40050, Message: "Error occured while invoking after execute api!",
		CNMessage: "调用单据的 AfterExecute API 失败！"}}

	// ErrTbBillInfoToBill TODO
	ErrTbBillInfoToBill = Err{Errno: Errno{Code: 40055, Message: "Error occured while transfer TbBillInfo  to Bill!",
		CNMessage: "转换 Bill Model 失败"}}

	// ErrCreateGCSJob TODO
	// job errors
	ErrCreateGCSJob = Errno{Code: 40100, Message: "Error occured while creating the gcs job.",
		CNMessage: "创建 GCS Job 失败！"}
	// ErrGetJobQueue TODO
	ErrGetJobQueue = Errno{Code: 40101, Message: "Error occured while get the gcs job queue.",
		CNMessage: "获取 job 失败 ！"}
	// ErrGetJobQueueNotFound TODO
	ErrGetJobQueueNotFound = Errno{Code: 40102, Message: "Job Queue Not Found.", CNMessage: "Job 不存在！"}
	// ErrDeleteJobQueue TODO
	ErrDeleteJobQueue = Errno{Code: 40103, Message: "Error occured while set the jobQueue to be deleted.",
		CNMessage: "删除 Job 失败!"}
	// ErrJobIDConvert2Int TODO
	ErrJobIDConvert2Int = Errno{Code: 40104, Message: "Error occured while converting the jobID to int.",
		CNMessage: "jobID 转换为int 出错!"}
	// ErrSubjobIDConvert2Int TODO
	ErrSubjobIDConvert2Int = Errno{Code: 40105, Message: "Error occured while converting the subjob_id to int.",
		CNMessage: "subjobID 转换为int 出错!"}

	// ErrPutJobQueueParam TODO
	ErrPutJobQueueParam = Errno{Code: 40106, Message: " param errors while puting a new JobQueue.",
		CNMessage: "创建 Job 时参数错误！"}
	// ErrJobQueueInputParam TODO
	ErrJobQueueInputParam = Errno{Code: 40107,
		Message:   "Some parameters is required in EnJobQueue: app,name,input,tag_id",
		CNMessage: "创建Job 时缺少下列参数:[app,name,input,tag_id]！"}
	// ErrJobQueueV1InputParam TODO
	ErrJobQueueV1InputParam = Errno{Code: 40107,
		Message:   "Some parameters is required in puting JobQueue: [app,name,distributions,payload,user]",
		CNMessage: "创建/修改 Job 时缺少下列参数:[app,name,distributions,payload,user]！"}
	// ErrJobQueueDistribution TODO
	ErrJobQueueDistribution = Errno{Code: 40108, Message: "JobQueue distributions format is wrong.",
		CNMessage: "创建 JobQueue 时 distributions 格式不正确！"}
	// ErrCheckJobQueue TODO
	ErrCheckJobQueue = Errno{Code: 40109, Message: "Error occured while checking JobQueue.",
		CNMessage: "检查 JobQueue 出错！"}
	// ErrJoqQueueIsNil TODO
	ErrJoqQueueIsNil = Errno{Code: 40110, Message: "JobQueue is Nil", CNMessage: "返回的Job 内容为空！"}
	// ErrCloneJoqQueues TODO
	ErrCloneJoqQueues = Errno{Code: 40113, Message: "Error occured while cloning jobQueues",
		CNMessage: "克隆 jobQueues 出错！"}

	// JobResultSuccess TODO
	JobResultSuccess = Errno{Code: 0, Message: "success", CNMessage: "success"}
	// JobResultRunning TODO
	JobResultRunning = Errno{Code: 40114, Message: "running", CNMessage: "running"}
	// JobResultFailed TODO
	JobResultFailed = Errno{Code: 40115, Message: "fail", CNMessage: "fail"}
	// JobResultOthers TODO
	JobResultOthers = Errno{Code: 40116, Message: "other job status", CNMessage: "other job status"}

	// ErrGetJobFeedbacks TODO
	// JobFeedback
	ErrGetJobFeedbacks = Errno{Code: 40210, Message: "Error occured while getting the gcs job feedback.",
		CNMessage: "获取 job feedback 信息失败！"}
	// ErrCreateGCSJobFeedback TODO
	ErrCreateGCSJobFeedback = Errno{Code: 40215, Message: "Error occured while creating the gcs jobFeedback.",
		CNMessage: "创建 GCS jobFeedback 失败！"}

	// InvalidJobIDorSubjobID TODO
	InvalidJobIDorSubjobID = Errno{Code: 40220, Message: "Invalid jobID or subJobID while getting the gcs job feedback.",
		CNMessage: "jobID or subJobID 无效！"}

	// ErrorJobNameBeEmpty TODO
	// JobDef errors
	ErrorJobNameBeEmpty = Errno{Code: 40300, Message: "JobName can not be empty.", CNMessage: "JobName 不能为空！"}
	// ErrorGetJobDef TODO
	ErrorGetJobDef = Errno{Code: 40302, Message: "Error occured while getting the gcs job_def",
		CNMessage: "获取 job_def 出现错误！"}

	// ErrorGetJobBlob TODO
	// JobBlob errors
	ErrorGetJobBlob = Errno{Code: 40302, Message: "Error occured while getting the gcs job_blob",
		CNMessage: "获取 job_blob 出现错误！"}

	// ErrorGetSubJobQueue TODO
	// subjob errors
	ErrorGetSubJobQueue = Errno{Code: 40800, Message: "Error occured while getting the gcs subjob ",
		CNMessage: "获取 subjob 出现错误！"}
	// ErrCreateSubJobQueue TODO
	ErrCreateSubJobQueue = Errno{Code: 40801, Message: "Error occured while creating the gcs subjobQueue.",
		CNMessage: "创建 GCS subjobQueue 失败！"}
	// ErrUpdateSubJobQueue TODO
	ErrUpdateSubJobQueue = Errno{Code: 40802, Message: "Error occured while updating the gcs subjobQueue.",
		CNMessage: "更新 GCS subjobQueue 失败！"}

	// SubJobUIDRequied TODO
	SubJobUIDRequied = Errno{Code: 40804, Message: "Subjob uid is required!", CNMessage: "Subjob uid 是必填项.！"}
	// ErrorUIDMustBeInt TODO
	ErrorUIDMustBeInt = Errno{Code: 40808, Message: "Subjob uid must be int!", CNMessage: "Subjob uid 必须是 int 类型.！"}
	// ErrSubjobQueueInputParam TODO
	ErrSubjobQueueInputParam = Errno{Code: 40812,
		Message: "Some parameters [JobID,Username,JobName,AtomjobList,JobInput] " +
			"are not meet the demands in saving SubjobQueue",
		CNMessage: "保存 SubjobQueue 时缺少下列参数:[JobID,Username,JobName,AtomjobList,JobInput]！"}
	// ErrJobFeedbackInputParam TODO
	ErrJobFeedbackInputParam = Errno{Code: 40815,
		Message: "Some parameters are not meet the demands in saving JobFeedback", CNMessage: "保存 JobFeedback 时参数不满足要求。"}
	// ErrGetGCSApps TODO
	// gcs app errors
	ErrGetGCSApps = Errno{Code: 40900, Message: "Error occured while getting gcs apps", CNMessage: "获取 GCS App 出现错误！"}
	// ErrGetCCApps TODO
	ErrGetCCApps = Errno{Code: 40902, Message: "Error occured while getting cc apps", CNMessage: "获取 App 出现错误！"}
	// ErrGetProjects TODO
	ErrGetProjects = Errno{Code: 40905, Message: "Error occured while getting projects", CNMessage: "获取 projects 出现错误！"}

	// ErrDBTransaction TODO
	// model operation errors
	ErrDBTransaction = Errno{Code: 50200, Message: "DB Transaction error.", CNMessage: "DB 事务发生错误！"}
	// ErrModelFunction TODO
	ErrModelFunction = Err{Errno: Errno{Code: 50201, Message: "Error occured while invoking model function.",
		CNMessage: "调用 DB model 方法发生错误！"}, Err: nil}

	// ErrSaveFlowAuditLog TODO
	ErrSaveFlowAuditLog = Errno{Code: 50203, Message: "Error occured while saving Flow Audit Log.",
		CNMessage: "存储单据审核日志记录出错！"}

	// ErrGetJSONArray TODO
	// data handle error
	ErrGetJSONArray = Errno{Code: 50300, Message: "Get simplejson Array error.", CNMessage: ""}
	// ErrConvert2Map TODO
	ErrConvert2Map = Errno{Code: 50301, Message: "Error occurred while converting the data to Map.",
		CNMessage: "Error occurred while converting the data to Map."}
	// ErrJSONMarshal TODO
	ErrJSONMarshal = Errno{Code: 50302, Message: "Error occurred while marshaling the data to JSON.",
		CNMessage: "Error occurred while marshaling the data to JSON."}
	// ErrReadEntity TODO
	ErrReadEntity = Errno{Code: 50303, Message: "Error occurred while parsing the request parameter.",
		CNMessage: "Error occurred while parsing the request parameter."}
	// ErrJSONUnmarshal TODO
	ErrJSONUnmarshal = Errno{Code: 50304, Message: "Error occurred while Unmarshaling the JSON to data model.",
		CNMessage: "Error occurred while Unmarshaling the JSON to data model."}
	// ErrBytesToMap TODO
	ErrBytesToMap = Errno{Code: 50307, Message: "Error occurred while converting bytes to map.",
		CNMessage: "Error occurred while converting bytes to map."}

	// ErrUserIsNotDBA TODO
	// user login and permission errors
	ErrUserIsNotDBA = Errno{Code: 50500, Message: "User is not dba."}
	// ErrNoSaveAndCommitPriv TODO
	ErrNoSaveAndCommitPriv = Errno{Code: 50502,
		Message: "User don't have gcs bill save and commit privs in this app.", CNMessage: "用户在当前 APP 上没有单据的保存和提交权限！"}
	// ErrNoBillAduitPriv TODO
	ErrNoBillAduitPriv = Errno{Code: 50504, Message: "User don't have gcs audit privs in this app.",
		CNMessage: "用户在当前 APP 上没有单据的审核权限！"}
	// ErrUserNotHaveBillRollbackPriv TODO
	ErrUserNotHaveBillRollbackPriv = Errno{Code: 50506, Message: "User don't have gcs rollback privs in this app.",
		CNMessage: "用户在当前 APP 上没有单据的驳回权限！"}
	// ErrUserHasNoPermission TODO
	ErrUserHasNoPermission = Errno{Code: 50508, Message: "User has no permission.", CNMessage: "当前用户没有权限！"}
	// ErrUserNotHaveBillClonePriv TODO
	ErrUserNotHaveBillClonePriv = Errno{Code: 50510, Message: "User don't have gcs bill clone privs in this app.",
		CNMessage: "用户没有当前单据的克隆权限！"}
	// ErrViewAppPriv TODO
	ErrViewAppPriv = Errno{Code: 50515, Message: "User have no priv to view this app!",
		CNMessage: "用户没有查看当前 APP 的权限！"}

	// ErrInvokeAPI TODO
	ErrInvokeAPI = Errno{Code: 50601, Message: "Error occurred while invoking API", CNMessage: "调用 API 发生错误！"}

	// ErrSnedRTX TODO
	// alarm errors
	ErrSnedRTX = Errno{Code: 50800, Message: "Error occurred while sending RTX message to user.",
		CNMessage: "发送 RTX 消息出现错误！"}

	// ErrPswNotIdentical TODO
	// grant privileges errors
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
	// ClonePrivilegesParameterCheckFail TODO
	ClonePrivilegesParameterCheckFail = Errno{Code: 51011, Message: "Parameter of Clone Privileges Check Fail",
		CNMessage: "克隆权限单据的参数检查失败"}
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
	CloudIdRequired         = Errno{Code: 51019, Message: "bk_cloud_id is required", CNMessage: "bk_cloud_id不能为空"}
	NotSupportedClusterType = Errno{Code: 51020, Message: "not supported cluster type", CNMessage: "不支持此集群类型"}
	ClusterTypeIsEmpty      = Errno{Code: 51021, Message: "Cluster type can't be empty", CNMessage: "cluster type不能为空"}
)
