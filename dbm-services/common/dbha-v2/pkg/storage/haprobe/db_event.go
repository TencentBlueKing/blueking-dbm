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
	"fmt"

	"dbm-services/common/dbha-v2/pkg/hanet"
)

// DbEventName db event name
type DbEventName string

const (
	// Compatible with V1
	DbEventNameRedisSwitchSuccessV1     DbEventName = "dbha_redis_switch_succ"
	DbEventNameRedisSwitchFailureV1     DbEventName = "dbha_redis_switch_err"
	DbEventNameMysqlSwitchSuccessV1     DbEventName = "dbha_mysql_switch_ok"
	DbEventNameMysqlSwitchFailureV1     DbEventName = "dbha_mysql_switch_err"
	DbEventNameRiakSwitchSuccessV1      DbEventName = "dbha_riak_switch_ok"
	DbEventNameRiakSwitchFailureV1      DbEventName = "dbha_riak_switch_err"
	DbEventNameSqlServerSwitchSuccessV1 DbEventName = "dbha_sqlserver_switch_ok"
	DbEventNameSqlServerSwitchFailureV1 DbEventName = "dbha_sqlserver_switch_err"
	DbEventNameMongoSwitchSuccessV1     DbEventName = "dbha_mongos_switch_succ"
	DbEventNameMongoSwitchFailureV1     DbEventName = "dbha_mongos_switch_err"
	DbEventNameDetectRedisAuthFailureV1 DbEventName = "dbha_detect_redis_auth_fail"
	DbEventNameDetectSshAuthFailureV1   DbEventName = "dbha_detect_ssh_auth_fail"
	DbEventNameDetectSshFailureV1       DbEventName = "dbha_detect_ssh_fail"
	DbEventNameDetectDbFailureV1        DbEventName = "dbha_detect_db_fail"
	DbEventNameDoubleCheckSshFailureV1  DbEventName = "dbha_doublecheck_ssh_fail"
	DbEventNameDoubleCheckAuthFailureV1 DbEventName = "dbha_doublecheck_auth_fail"
	DbEventNameGlobalMonitorV1          DbEventName = "dbha_global_monitor"
	DbEventNameApiFailureV1             DbEventName = "dbha_call_api_fail"

	// V2
	DbEventNameDetectFailure    DbEventName = "dbha_detect_db_failure"
	DbEventNameDetectSSHFailure DbEventName = "dbha_detect_ssh_failure"
	DbEventNameProbeOffline     DbEventName = "dbha_probe_offline"
)

// DbEventNameReason db event name reason
type DbEventNameReason int

const (
	DbEventNameReasonConnectionException DbEventNameReason = iota
	DbEventNameReasonAuthException
	DbEventNameReasonSSHAuthException
	DbEventNameReasonMissedProbe
)

// DbType  db type
type DbType string

const (
	DbTypeMysql DbType = "mysql"
)

// DbEvent Include some exception events
type DbEvent struct {
	Name       DbEventName       `json:"name"`
	Reason     DbEventNameReason `json:"type"`
	DbTypeName DbType            `json:"dbTypeName"`
	Endpoint   *hanet.Endpoint   `json:"endpoint,omitempty"`
	Message    string            `json:"message"`
}

func (t DbEventName) String() string {
	return string(t)
}

func (t DbEventNameReason) String() string {
	switch t {
	case DbEventNameReasonConnectionException:
		return "connection exception"

	case DbEventNameReasonAuthException:
		return "auth failure"

	case DbEventNameReasonSSHAuthException:
		return "ssh auth failure"

	case DbEventNameReasonMissedProbe:
		return "missed probe"

	default:
		return fmt.Sprintf("unknown event name reason: %d", t)
	}
}

func (t DbType) String() string {
	return string(t)
}
