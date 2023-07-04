/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

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
func (err *Errno) Addf(format string, args ...interface{}) error {
	return err.Add(fmt.Sprintf(format, args...))
}

// Add TODO
func (err *Errno) Add(message string) error {
	switch lang {
	case "zh_CN":
		err.CNMessage = fmt.Sprintf("[%s]: %s", err.CNMessage, message)
		return err
	case "en_US":
		err.Message = fmt.Sprintf("[%s]: %s", err.Message, message)
		return err
	default:
		err.CNMessage = fmt.Sprintf("[%s]: %s", err.CNMessage, message)
		return err
	}
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
}

// AddErr TODO
func (err *Errno) AddErr(xerr error) error {
	message := xerr.Error()
	if xerr == nil {
		message = "error is nil"
	}
	return err.Add(message)
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
