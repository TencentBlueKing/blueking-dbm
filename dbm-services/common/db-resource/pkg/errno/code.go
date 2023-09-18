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
	// ErrString2Int TODO
	ErrString2Int = Errno{Code: 10010, Message: "Error occurred while convert string to int."}
	// ErrorJsonToMap TODO
	ErrorJsonToMap = Errno{Code: 10030, Message: "Error occured while converting json to Map.",
		CNMessage: "Json 转为 Map 出现错误！"}
	// ErrorUIDBeZero TODO
	ErrorUIDBeZero = Errno{Code: 10035, Message: "uid can not be 0!", CNMessage: "uid 不能为 0.！"}

	// ErrTypeAssertion TODO
	ErrTypeAssertion = Errno{Code: 10040, Message: "Error occurred while doing type assertion."}
	// ErrParameterRequired TODO
	ErrParameterRequired = Errno{Code: 10050, Message: "Input paramter required"}
	// StartBiggerThanEndTime TODO
	StartBiggerThanEndTime = Errno{Code: 10060, Message: "Start time is bigger than end time."}

	// ErrInputParameter TODO
	ErrInputParameter = Errno{Code: 10201, Message: "input pramater error.", CNMessage: "输入参数错误"}

	// ErrInvokeAPI TODO
	// call other service error
	ErrInvokeAPI = Errno{Code: 15000, Message: "Error occurred while invoking API", CNMessage: "调用 API 发生错误！"}

	// InvalidHttpStatusCode TODO
	InvalidHttpStatusCode = Errno{Code: 15015, Message: "Invalid http status code", CNMessage: "无效的 http 状态码！"}

	// ErrDoNotHavePrivs TODO
	// user errors
	ErrDoNotHavePrivs = Errno{Code: 20106, Message: "User don't have Privs."}
	// ErrUserIsEmpty TODO
	ErrUserIsEmpty = Errno{Code: 20110, Message: "User can't be empty.", CNMessage: "user 不能为空！"}

	// dbrms

	// ErrDBQuery TODO
	// model operation errors
	ErrDBQuery = Errno{Code: 50200, Message: "DB Query error.", CNMessage: "查询DB错误！"}
	// ErrModelFunction TODO
	ErrModelFunction = Err{Errno: Errno{Code: 50201, Message: "Error occured while invoking model function.",
		CNMessage: "调用 DB model 方法发生错误！"}, Err: nil}

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
	// ErrorResourceinsufficient TODO
	// dbrms
	// ErrorResourceinsufficient TODO
	ErrorResourceinsufficient = Errno{Code: 60001, Message: "resource insufficient", CNMessage: "资源不足"}
)
