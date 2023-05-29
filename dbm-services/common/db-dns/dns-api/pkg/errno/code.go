package errno

var (
	// OK TODO
	// Common errors
	OK = &Errno{Code: 0, Message: "OK"}
	// InternalServerError TODO
	InternalServerError = &Errno{Code: 10001, Message: "Internal server error"}
	// ErrBind TODO
	ErrBind = &Errno{Code: 10002, Message: "Error occurred while binding the request body to the struct."}

	// ErrValidation TODO
	ErrValidation = &Errno{Code: 20001, Message: "Validation failed."}
	// ErrDatabase TODO
	ErrDatabase = &Errno{Code: 20002, Message: "Database error."}
	// ErrToken TODO
	ErrToken = &Errno{Code: 20003, Message: "Error occurred while signing the JSON web token."}

	// ErrEncrypt TODO
	// user errors
	ErrEncrypt = &Errno{Code: 20101, Message: "Error occurred while encrypting the user password."}
	// ErrUserNotFound TODO
	ErrUserNotFound = &Errno{Code: 20102, Message: "The user was not found."}
	// ErrTokenInvalid TODO
	ErrTokenInvalid = &Errno{Code: 20103, Message: "The token was invalid."}
	// ErrPasswordIncorrect TODO
	ErrPasswordIncorrect = &Errno{Code: 20104, Message: "The password was incorrect."}

	// ErrRoleNotFound TODO
	// role errors
	ErrRoleNotFound = &Err{Code: 30000, Message: "The role was not found."}
)
