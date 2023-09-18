// Package errno TODO
package errno

import (
	"fmt"
)

// Errno TODO
type Errno struct {
	Code      int
	Message   string
	CNMessage string
}

const lang = "zh_CN"

// Error 用于错误处理
func (err Errno) Error() string {
	switch lang {
	case "zh_CN":
		return err.CNMessage
	case "en_US":
		return err.Message
	default:
		return err.CNMessage
	}
}

// Addf TODO
func (err Errno) Addf(format string, args ...interface{}) error {
	return err.Add(fmt.Sprintf(format, args...))
}

// Add TODO
func (err Errno) Add(message string) error {
	switch lang {
	case "zh_CN":
		err.CNMessage += message
	case "en_US":
		err.Message += message
	default:
		err.CNMessage += message
	}
	return err
}

// Err represents an error
type Err struct {
	Errno
	Err error
}

// New TODO
func New(errno Errno, err error) *Err {
	return &Err{Errno: errno, Err: err}
}

// Add TODO
func (err Err) Add(message string) error {
	switch lang {
	case "zh_CN":
		err.CNMessage += message
		return err
	case "en_US":
		err.Message += message
		return err
	default:
		err.CNMessage += message
		return err
	}
}

// SetMsg TODO
func (err Err) SetMsg(message string) error {
	err.Message = message
	return err
}

// SetCNMsg TODO
func (err Err) SetCNMsg(cnMessage string) error {
	err.CNMessage = cnMessage
	return err
}

// Addf TODO
func (err Err) Addf(format string, args ...interface{}) error {
	return err.Add(fmt.Sprintf(format, args...))
}

// DecodeErr TODO
func DecodeErr(err error) (int, string) {

	var CN bool = true

	if err == nil {
		return OK.Code, OK.Message
	}

	switch typed := err.(type) {
	case Err:
		if CN {
			return typed.Code, typed.CNMessage
		} else {
			return typed.Code, typed.Message
		}
	case Errno:
		if CN {
			return typed.Code, typed.CNMessage
		} else {
			return typed.Code, typed.Message
		}
	default:
	}
	return InternalServerError.Code, err.Error()
}
