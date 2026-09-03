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

package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestWriteRedisReply_PINGHELLOINFO(t *testing.T) {
	cases := []struct {
		cmd  string
		want string
		cont bool
	}{
		{cmd: "PING", want: "+PONG\r\n", cont: true},
		{cmd: "HELLO", want: "-ERR unknown command 'HELLO'\r\n", cont: true},
		{cmd: "AUTH", want: "+OK\r\n", cont: true},
		{cmd: "QUIT", want: "+OK\r\n", cont: false},
	}
	for _, tc := range cases {
		var buf bytes.Buffer
		cont := writeRedisReply(&buf, tc.cmd)
		if cont != tc.cont {
			t.Errorf("cmd: %s continue: %v, want: %v", tc.cmd, cont, tc.cont)
		}
		if buf.String() != tc.want {
			t.Errorf("cmd: %s reply: %q, want: %q", tc.cmd, buf.String(), tc.want)
		}
	}

	var info bytes.Buffer
	if !writeRedisReply(&info, "INFO") {
		t.Fatal("INFO should keep the connection open")
	}
	got := info.String()
	if !strings.HasPrefix(got, "$") || !strings.Contains(got, "role:master") {
		t.Fatalf("INFO reply missing role:master, bytes: %d", len(got))
	}
}
