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

import (
	"errors"
	"fmt"
)

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
	Timeout
	Exited

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
func Newf(c Code, format string, args ...any) *Error {
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
func NewCustomf(c int, format string, args ...any) *Error {
	msg := fmt.Sprintf(format, args...)
	return &Error{code: c, message: msg}
}

// NewCustomE is used to create an error with custom code value.
func NewCustomE(c int, err error) *Error {
	if err == nil {
		return nil
	}

	return &Error{code: c, message: err.Error(), origin: err}
}

// Error represents a custom error with code and message
type Error struct {
	code    int
	message string
	origin  error
}

// Code returns the error code
func (e *Error) Code() int {
	return e.code
}

// HasCode checks if the error has the specified code
func (e *Error) HasCode(c Code) bool {
	return e.code == c.Int()
}

// RootCause returns the root cause of the error
func (e *Error) RootCause() error {
	visited := make(map[*Error]bool)
	current := e

	for {
		if visited[current] {
			// found a cycle
			return current
		}
		visited[current] = true

		if current.origin == nil {
			return current
		}

		if rootErr, ok := current.origin.(*Error); ok {
			current = rootErr
			continue
		}

		return current.origin
	}
}

// Error returns the error message string
func (e *Error) Error() string {
	return e.message
}

// Is checks if the error is the specified error
func (e *Error) Is(err error) bool {
	if err == nil {
		return false
	}

	if targetErr, ok := err.(*Error); ok {
		return targetErr.code == e.code
	}

	if e.origin != nil {
		return errors.Is(e.origin, err)
	}

	return false
}

// Unwrap returns the wrapped error
func (e *Error) Unwrap() error {
	return e.origin
}
