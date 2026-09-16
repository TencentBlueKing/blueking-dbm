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

package hamysql

import (
	"regexp"
)

const (
	sanitizedSecret      = "<secret>"
	maxSanitizedErrorLen = 256
)

var (
	dsnFragmentPattern    = regexp.MustCompile(`[^\s]+:[^\s]+@(tcp|unix)\([^)]+\)[^\s]*`)
	dsnCredentialPattern  = regexp.MustCompile(`([^\s:/]+):([^@\s]+)@`)
	sensitiveParamPattern = regexp.MustCompile(`(?i)(password|token|passwd|pwd)\s*=\s*[^\s&]+`)
)

// SanitizeConnectionError returns a desensitized error summary safe for harvest reporting.
// Passwords, tokens, and DSN credential segments are redacted. MySQL error codes and server
// messages are preserved when they do not embed credentials. err may be nil.
func SanitizeConnectionError(err error) string {
	if err == nil {
		return ""
	}

	msg := err.Error()
	msg = dsnFragmentPattern.ReplaceAllString(msg, "<redacted-dsn>")
	msg = dsnCredentialPattern.ReplaceAllString(msg, "$1:"+sanitizedSecret+"@")
	msg = sensitiveParamPattern.ReplaceAllString(msg, "$1="+sanitizedSecret)

	if len(msg) > maxSanitizedErrorLen {
		msg = msg[:maxSanitizedErrorLen]
	}
	return msg
}
