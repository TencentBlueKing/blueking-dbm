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

package harvest

import "testing"

func TestParseRedisInfoToMap(t *testing.T) {
	info := "# Replication\nrole:master\nconnected_slaves:0\n\n# Keyspace\ndb0:keys=1,expires=0,avg_ttl=0\n"

	result := parseRedisInfoToMap(info)

	if result["role"] != "master" {
		t.Errorf("expected role master, got %q", result["role"])
	}
	if result["connected_slaves"] != "0" {
		t.Errorf("expected connected_slaves 0, got %q", result["connected_slaves"])
	}
	if _, ok := result["# Replication"]; ok {
		t.Errorf("comment line should be skipped")
	}
}
