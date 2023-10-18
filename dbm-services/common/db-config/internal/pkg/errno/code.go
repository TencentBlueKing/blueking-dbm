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

	// ErrTypeAssertion TODO
	ErrTypeAssertion = Errno{Code: 10040, Message: "Error occurred while doing type assertion."}
	// ErrParameterRequired TODO
	ErrParameterRequired = Errno{Code: 10050, Message: "Input paramter required"}
	// ErrBKBizIDIsEmpty TODO
	ErrBKBizIDIsEmpty = Errno{Code: 10200, Message: "BKBizID is empty!", CNMessage: "BKBizID 名字不能为空！"}

	// ErrInputParameter TODO
	ErrInputParameter = Errno{Code: 10201, Message: "input pramater error.", CNMessage: "输入参数错误"}

	// ErrInvokeAPI TODO
	// call other service error
	ErrInvokeAPI = Errno{Code: 15000, Message: "Error occurred while invoking API", CNMessage: "调用 API 发生错误！"}
	// ErrInvokeSaveBillAPI TODO
	ErrInvokeSaveBillAPI = Errno{Code: 15003, Message: "Error occurred while invoking SaveBill API",
		CNMessage: "调用 SaveBill API 发生错误！"}
	// GreaterThanOneConfigValue TODO
	GreaterThanOneConfigValue = Errno{Code: 15010, Message: "number of  gcs config value  is greater than 1",
		CNMessage: "获取 GCS config 的 value 个数超过 1 ！"}
	// InvalidHttpStatusCode TODO
	InvalidHttpStatusCode = Errno{Code: 15015, Message: "Invalid http status code", CNMessage: "无效的 http 状态码！"}

	// ErrRecordNotFound TODO
	// model operation errors
	ErrRecordNotFound = Errno{Code: 50202, Message: "There is no records in gcs database.", CNMessage: "GCS 数据库未找到对应的记录！"}

	// ErrJSONMarshal TODO
	// data handle error
	ErrJSONMarshal = Errno{Code: 50302, Message: "Error occurred while marshaling the data to JSON.",
		CNMessage: "Error occurred while marshaling the data to JSON."}
	// ErrReadEntity TODO
	ErrReadEntity = Errno{Code: 50303, Message: "Error occurred while parsing the request parameter.",
		CNMessage: "Error occurred while parsing the request parameter."}
	// ErrJSONUnmarshal TODO
	ErrJSONUnmarshal = Errno{Code: 50304, Message: "Error occurred while Unmarshaling the JSON to data model.",
		CNMessage: "Error occurred while Unmarshaling the JSON to data model."}

	// ErrDuplicateItem TODO
	ErrDuplicateItem = Errno{Code: 10000, Message: "duplicate conf_name", CNMessage: "配置项重复"}
	// ErrNamespaceType TODO
	ErrNamespaceType = Errno{Code: 10000, Message: "invalid namespace or conf_type or conf_file",
		CNMessage: "namespace,conf_type,conf_file 参数错误"}
	// ErrUnversionable TODO
	ErrUnversionable = Errno{Code: 10000, Message: "this namespace conf_type is unVersion-able",
		CNMessage: "该 namespace conf_type 不支持版本化"}
	// ErrVersionable TODO
	ErrVersionable = Errno{Code: 10000,
		Message:   "version-able config file should use SaveOnly/SaveAndPublish api",
		CNMessage: "可版本化配置需使用 SaveOnly/SaveAndPublish 接口"}
	// ErrConflictWithLowerConfigLevel TODO
	ErrConflictWithLowerConfigLevel = Errno{Code: 8705002, Message: "has conflicts with lower config level",
		CNMessage: "与下层级配置存在冲突，会覆盖下级配置"}
	// ErrConfigLevel TODO
	ErrConfigLevel = Errno{Code: 10002, Message: "level should not be the same", CNMessage: "出现重复level_name"}
	// ErrNodeNotFound TODO
	ErrNodeNotFound = Errno{Code: 10005, Message: "level node_id not found", CNMessage: "没有找到 node_id"}
	// ErrConfFile TODO
	ErrConfFile = Errno{Code: 10005, Message: "conf_file definition error", CNMessage: "配置文件定义错误"}
	// ErrLevelName TODO
	ErrLevelName = Errno{Code: 10006, Message: "illegal level_name", CNMessage: "level_name 非法"}
	// ErrOnlyLevelConfigAllowed TODO
	ErrOnlyLevelConfigAllowed = Errno{Code: 10007, Message: "only level_config is allowed to be applied by default",
		CNMessage: "只有 level_config 才能直接应用 config"}
	ErrDecryptValue = Errno{Code: 10007, Message: "decrypt config value failed", CNMessage: "解密出现异常"}
)
