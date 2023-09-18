package errno

var (
	// OK TODO
	OK = &Errno{Code: 0, Message: "OK"}

	// ErrInterval TODO
	// types error, prefix is 100
	ErrInterval = &Errno{Code: 10001, Message: "Internal server error", CNMessage: "内部未知错误"}
	// ErrHttpStatusCode TODO
	ErrHttpStatusCode = &Errno{Code: 10002, Message: "Invalid http status code", CNMessage: "http请求状态码不对"}
	// ErrHttpResponse TODO
	ErrHttpResponse = &Errno{Code: 10003, Message: "Invalid http response", CNMessage: "http请求返回异常"}
	// ErrInvokeApi TODO
	ErrInvokeApi = &Errno{Code: 10004, Message: "Invoke api failed", CNMessage: "调用api出错"}
	// ErrJSONMarshal TODO
	ErrJSONMarshal = &Errno{Code: 10005, Message: "Error occurred while marshal the data to JSON.",
		CNMessage: "序列化JSON数据出错"}
	// ErrJSONUnmarshal TODO
	ErrJSONUnmarshal = &Errno{Code: 10006, Message: "Error occurred while unmarshal the JSON to data model.",
		CNMessage: "反序列号JSON数据出错"}
	// ErrGetInstanceInfo TODO
	ErrGetInstanceInfo = &Errno{Code: 10007, Message: "Get instance info failed", CNMessage: "获取实例信息失败"}
	// ErrAppNotFound TODO
	ErrAppNotFound = &Errno{Code: 10008, Message: "Get app info failed", CNMessage: "获取业务信息失败"}

	// api error, prefix is 200

	// ErrMultiMaster TODO
	// mysql error, prefix is 300
	ErrMultiMaster = &Errno{Code: 30001, Message: "Multi master found", CNMessage: "同一主机同时存在实例角色master和slave"}
	// ErrSwitchNumUnMatched TODO
	// dead host's instance num not equal to its switch number
	ErrSwitchNumUnMatched = &Errno{Code: 30002, Message: "instances number is %d, switch number is %d, unmatched",
		CNMessage: "实例个数%d与切换个数%d不匹配"}
	// ErrRemoteQuery TODO
	ErrRemoteQuery = &Errno{Code: 30003, Message: "do remote query failed", CNMessage: "调用remoteQuery失败"}
	// ErrRemoteExecute TODO
	ErrRemoteExecute = &Errno{Code: 30004, Message: "do remote execute failed", CNMessage: "调用remoteExecute失败"}
	// ErrIOTreadState TODO
	ErrIOTreadState = &Errno{Code: 30005, Message: "slave IO_THREAD is not ok", CNMessage: "IO_THREAD异常"}
	// ErrSQLTreadState TODO
	ErrSQLTreadState = &Errno{Code: 30006, Message: "slave SQL_THREAD is not ok", CNMessage: "SQL_THREAD异常"}
	// ErrSlaveStatus TODO
	ErrSlaveStatus = &Errno{Code: 30007, Message: "get slave status abnormal", CNMessage: "获取slave status异常"}
	// proxy error, prefix is 400
)
