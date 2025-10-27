/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package gerrors

import "fmt"

// Code dbha global error code type
type Code int

// Int returns the integer value of the error code
func (c Code) Int() int {
	return int(c)
}

// Internal Error Code
const (
	Unknown Code = iota - 2
	Failure
	Success
	Timeout
	Exited

	NotFound
	NotExist
	NetException
	QueueFull
	Unimplemented
	Unsupported

	InvalidParameter
	InvalidUrl
	InvalidJson
	InvalidYaml
	InvalidHttpMethod
	InvalidConfiguration

	InternalServerFailure
	HttpRequestFailure

	ProbeFailure

	BkMonitorFailure
	BkGseFailure
	KafkaFailure
	GrpcFailure
	SshFailure
	EtcdFailure
	MysqlFailure
	NodeAbnormal
)

// New create a internal error.
func New(c Code, msg string) *Error {
	return NewCustom(c.Int(), msg)
}

// Newf create a internal error with format.
func Newf(c Code, format string, args ...interface{}) *Error {
	return NewCustomf(c.Int(), format, args...)
}

// NewE create a internal error withe the error
func NewE(c Code, err error) *Error {
	return NewCustomE(c.Int(), err)
}

// NewCustom is used to create an error with custom code value.
func NewCustom(c int, msg string) *Error {
	return &Error{code: c, message: msg}
}

// NewCustomf is used to create an error with custom code value.
func NewCustomf(c int, format string, args ...interface{}) *Error {
	msg := fmt.Sprintf(format, args...)
	return &Error{code: c, message: msg}
}

// NewCustomE is used to create an error with custom code value.
func NewCustomE(c int, err error) *Error {
	if err == nil {
		return nil
	}

	return &Error{code: c, message: err.Error()}
}

// Error represents a custom error with code and message
type Error struct {
	code    int
	message string
}

// Code returns the error code
func (e *Error) Code() int {
	return e.code
}

// CodeIs checks if the error code matches the given code
func (e *Error) CodeIs(c Code) bool {
	return e.code == c.Int()
}

// Error returns the error message string
func (e *Error) Error() string {
	return e.message
}
