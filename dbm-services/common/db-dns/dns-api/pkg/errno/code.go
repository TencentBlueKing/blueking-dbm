package errno

var (
	// OK 正常状态
	OK = &Errno{Code: 0, Message: "OK"}
	// InternalServerError 网络错误
	InternalServerError = &Errno{Code: 10001, Message: "Internal server error"}
)
