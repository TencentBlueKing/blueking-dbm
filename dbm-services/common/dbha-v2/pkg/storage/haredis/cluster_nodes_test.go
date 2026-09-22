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

func TestParseClusterNodes(t *testing.T) {
	raw := `1111111111111111111111111111111111111111 127.0.0.1:30001@40001 myself,master - 0 0 1 connected 0-8191
2222222222222222222222222222222222222222 127.0.0.2:30002@40002 slave 1111111111111111111111111111111111111111 0 0 1 connected
`
	nodes := ParseClusterNodes(raw)
	if len(nodes) != 2 {
		t.Fatalf("expected 2 nodes, got %d", len(nodes))
	}
	if nodes[0].Role != "master" || nodes[0].Address != "127.0.0.1:30001" || nodes[0].Slots != "0-8191" {
		t.Fatalf("unexpected master node: %+v", nodes[0])
	}
	if nodes[1].Role != "slave" || nodes[1].MasterID != "1111111111111111111111111111111111111111" {
		t.Fatalf("unexpected slave node: %+v", nodes[1])
	}
}
