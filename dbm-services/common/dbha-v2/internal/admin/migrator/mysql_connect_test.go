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

package migrator

import (
	"net"
	"strconv"
	"testing"
)

func TestConnectFailureLeavesNoConnection(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	if err = listener.Close(); err != nil {
		t.Fatal(err)
	}

	store := newMySQLStore("", "127.0.0.1", port, "migrate_user", "")
	if store.proto != "tcp" || store.Endpoint() != net.JoinHostPort("127.0.0.1", strconv.Itoa(port)) {
		t.Fatalf("store defaults, proto: %s, endpoint: %s", store.proto, store.Endpoint())
	}
	if err = store.connect(); err == nil {
		t.Fatal("connect to a closed port succeeded")
	}
	if store.conn != nil || store.db != nil {
		t.Fatal("failed connect left a connection behind")
	}
	if _, err = store.Identity(); err == nil {
		t.Fatal("identity on a closed port succeeded")
	}
	if err = store.Unlock(); err != nil {
		t.Fatalf("unlock after a failed connect, errmsg: %s", err)
	}
}
