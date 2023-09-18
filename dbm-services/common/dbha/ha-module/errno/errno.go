// Package errno TODO
package errno

import (
	"fmt"
)

// Errno struct
type Errno struct {
	Code      int
	Message   string
	CNMessage string
}

// Lang TODO
var Lang = "en_US"

// Error 用于错误处理
// get string error
func (err Errno) Error() string {
	switch Lang {
	case "zh_CN":
		return err.CNMessage
	case "en_US":
		return err.Message
	default:
		return err.Message
	}
}

// Addf error info according to format
func (err Errno) Addf(format string, args ...interface{}) error {
	return err.Add(fmt.Sprintf(format, args...))
}

// Errorf format
func (err Errno) Errorf(args ...interface{}) error {
	switch Lang {
	case "zh_CN":
		err.CNMessage = fmt.Sprintf(err.CNMessage, args...)
	case "en_US":
		err.Message = fmt.Sprintf(err.Message, args...)
	default:
		err.Message = fmt.Sprintf(err.Message, args...)
	}

	return err
}

// Add error info
func (err Errno) Add(message string) error {
	switch Lang {
	case "zh_CN":
		err.CNMessage += message
	case "en_US":
		err.Message += message
	default:
		err.Message += message
	}
	return err
}

// Err or with errno
type Err struct {
	Errno
	Err error
}

// New error
func New(errno *Errno, err error) *Err {
	return &Err{Errno: *errno, Err: err}
}

// SetMsg TODO
// set error message
func (err Err) SetMsg(message string) error {
	err.Message = message
	return err
}

// SetCNMsg TODO
// set cn error message
func (err Err) SetCNMsg(cnMessage string) error {
	err.CNMessage = cnMessage
	return err
}

// Error 用于错误处理
// get error string
func (err Err) Error() string {
	message := err.Message
	switch Lang {
	case "zh_CN":
		message = err.CNMessage
	case "en_US":
		message = err.Message
		err.Message += message
	default:
		message = err.Message
	}
	return fmt.Sprintf("Err - code: %d, message: %s, error: %s", err.Code, message, err.Err.Error())
}
