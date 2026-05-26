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

package redis

import (
	"strings"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// ClassifyConnectionError maps redis connection errors to event semantics used by analysis.
func ClassifyConnectionError(err error) (haprobe.DbEventName, haprobe.DbEventNameReason) {
	if err == nil {
		return haprobe.DbEventNameDetectFailure, haprobe.DbEventNameReasonConnectionException
	}

	errMsg := strings.ToUpper(err.Error())
	if strings.Contains(errMsg, "NOAUTH") ||
		strings.Contains(errMsg, "WRONGPASS") ||
		strings.Contains(errMsg, "AUTH") {
		return haprobe.DbEventNameDetectRedisAuthFailureV1, haprobe.DbEventNameReasonAuthException
	}

	return haprobe.DbEventNameDetectFailure, haprobe.DbEventNameReasonConnectionException
}
