// Package errno TODO
package errno

import (
	"fmt"

	"github.com/spf13/viper"
)

// Errno TODO
type Errno struct {
	Code      int
	Message   string
	CNMessage string
}

var lang = viper.GetString("lang")

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
		return err
	case "en_US":
		err.Message += message
		return err
	default:
		err.CNMessage += message
		return err
	}
	return err
}

// AddBefore TODO
func (err Errno) AddBefore(message string) error {
	switch lang {
	case "zh_CN":
		err.CNMessage = message + err.CNMessage
		return err
	case "en_US":
		err.Message = message + err.Message
		return err
	default:
		err.CNMessage = message + err.CNMessage
		return err
	}
	return err
}

// Err TODO
type Err struct {
	Errno
	Err error
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
	return err
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
	fmt.Printf("%s", err.Error())
	return InternalServerError.Code, err.Error()
}
