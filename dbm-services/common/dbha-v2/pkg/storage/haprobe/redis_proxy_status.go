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

// RedisTwemproxyStatus Twemproxy proxy status
type RedisTwemproxyStatus struct {
	UptimeInSeconds    int64                   `json:"uptime,omitempty"`
	TotalConnections   int64                   `json:"total_connections,omitempty"`
	CurrentConnections int64                   `json:"curr_connections,omitempty"`
	Backends           []RedisTwemproxyBackend `json:"backends,omitempty"`
}

// RedisTwemproxyBackend Twemproxy backend server status
type RedisTwemproxyBackend struct {
	Server            string `json:"server,omitempty"`
	ServerConnections int64  `json:"server_connections,omitempty"`
	ServerEOF         int64  `json:"server_eof,omitempty"`
	ServerErr         int64  `json:"server_err,omitempty"`
	ServerTimedout    int64  `json:"server_timedout,omitempty"`
	RequestBytes      int64  `json:"request_bytes,omitempty"`
	ResponseBytes     int64  `json:"response_bytes,omitempty"`
	InQueue           int64  `json:"in_queue,omitempty"`
	OutQueue          int64  `json:"out_queue,omitempty"`
}

// RedisPredixyStatus Predixy proxy status
type RedisPredixyStatus struct {
	UptimeInSeconds    int64                 `json:"uptime_in_seconds,omitempty"`
	TotalConnections   int64                 `json:"total_connections,omitempty"`
	CurrentConnections int64                 `json:"curr_connections,omitempty"`
	Backends           []RedisPredixyBackend `json:"backends,omitempty"`
}

// RedisPredixyBackend Predixy backend server status
type RedisPredixyBackend struct {
	Server      string `json:"server,omitempty"`
	Role        string `json:"role,omitempty"`
	Group       string `json:"group,omitempty"`
	DC          string `json:"dc,omitempty"`
	Connections int64  `json:"connections,omitempty"`
	Requests    int64  `json:"requests,omitempty"`
	Responses   int64  `json:"responses,omitempty"`
	SendBytes   int64  `json:"send_bytes,omitempty"`
	RecvBytes   int64  `json:"recv_bytes,omitempty"`
}
