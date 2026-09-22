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

package haredis

import "testing"

func TestParsePredixyInfoServers(t *testing.T) {
	raw := `# Servers
Server:127.0.0.1:30000
Role:master
Group:0
DC:0
CurrentIsFail:0
Connections:1

Server:127.0.0.2:30000
Role:slave
Group:0
DC:0
CurrentIsFail:1
Connections:0
`
	servers := ParsePredixyInfoServers(raw)
	if len(servers) != 2 {
		t.Fatalf("expected 2 servers, got %d", len(servers))
	}
	if servers[0].Server != "127.0.0.1:30000" || servers[0].CurrentIsFail != 0 {
		t.Fatalf("unexpected first server: %+v", servers[0])
	}
	if servers[1].Server != "127.0.0.2:30000" || servers[1].CurrentIsFail != 1 {
		t.Fatalf("unexpected second server: %+v", servers[1])
	}

	md5a := servers.MD5String()
	reordered := ParsePredixyInfoServers(`# Servers
Server:127.0.0.2:30000
Role:slave
Group:0
DC:0
CurrentIsFail:1
Connections:0

Server:127.0.0.1:30000
Role:master
Group:0
DC:0
CurrentIsFail:0
Connections:1
`)
	if reordered.MD5String() != md5a {
		t.Fatalf("md5 should be stable regardless of order")
	}
}
