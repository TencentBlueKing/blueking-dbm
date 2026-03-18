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

// Package constant defines shared constants for dbha-v2 (delimiters, defaults, timeouts, etc.).
package constant

import "time"

const (
	Delimiter                         = ";"
	DbmApiNameMetadata                = "metadata"
	DefaultLocalIPInterface           = "eth1"
	DefaultClientPingTime             = 5 * time.Second
	DefaultServerPingTime             = 5 * time.Minute
	DefaultPingTimeout                = 10 * time.Second
	DefaultKeepAliveMiniTime          = 5 * time.Minute
	DefaultMaxReceiveMessageSize      = 1024 * 1024 * 10
	DefaultMaxSendMessageSize         = 1024 * 1024 * 10
	DefaultClientReconnectInterval    = 5 * time.Second
	DefaultClientMaxReconnectAttempts = 10
	DefaultReceiverBufferSize         = 1024
	DefaultAdminBufferSize            = 1024
	DefaultServiceTimerInterval       = 3 * time.Second
	DefaultServiceUpdateTimeout       = 3 * time.Second
)

const (
	DirModePermission  = 0755
	FileModePermission = 0644
)
