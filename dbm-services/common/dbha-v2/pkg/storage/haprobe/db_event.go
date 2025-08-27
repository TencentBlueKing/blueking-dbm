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

package haprobe

import (
	"dbm-services/common/dbha-v2/pkg/hanet"
	"fmt"
)

// DbEventName db event name
type DbEventName string

const (
	DbEventNameDetectFailure    DbEventName = "dbha_detect_db_failure"
	DbEventNameDetectSSHFailure DbEventName = "dbha_detect_ssh_failure"
)

// DbEventType db event type
type DbEventType int

const (
	DbEventTypeConnectionException DbEventType = iota
	DbEventTypeAuthException
	DbEventTypeSSHAuthException
)

// DbType  db type
type DbType int

const (
	DbTypeNameMysql DbType = iota
)

// DbEvent Include some exception events
type DbEvent struct {
	Name       DbEventName     `json:"name"`
	Type       DbEventType     `json:"type"`
	DbTypeName DbType          `json:"dbTypeName"`
	Endpoint   *hanet.Endpoint `json:"endpoint,omitempty"`
	Message    string          `json:"message"`
}

func (t DbEventName) String() string {
	return string(t)
}

func (t DbEventType) String() string {
	switch t {
	case DbEventTypeConnectionException:
		return "connection exception"

	case DbEventTypeAuthException:
		return "auth failure"

	case DbEventTypeSSHAuthException:
		return "ssh auth failure"

	default:
		return fmt.Sprintf("unknown event type: %d", t)
	}
}

func (t DbType) String() string {
	switch t {
	case DbTypeNameMysql:
		return "mysql"

	default:
		return fmt.Sprintf("unknown db type name: %d", t)
	}
}
