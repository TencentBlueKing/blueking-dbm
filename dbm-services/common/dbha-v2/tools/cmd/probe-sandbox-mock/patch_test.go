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
	"strings"
	"testing"
)

func TestPatchProbeYAMLText_PreservesIndent(t *testing.T) {
	in := strings.Join([]string{
		"name: probe",
		"pidFile: ./pids/probe.pid",
		"reporter:",
		"    name: gse",
		"    endpoint: 127.0.0.1:1",
		"    dataID: 1",
		"    connTimeout: 2s",
		"harvester:",
		"    mysql:",
		"        user: sandbox",
		"log:",
		"    path: ./logs/probe.log",
		"    level: info",
		"    fileCount: 10",
		"",
	}, "\n")

	got := patchProbeYAMLText(in, "127.0.0.1:19100", "/tmp/probe-sandbox/logs/probe.log")
	wantLines := []string{
		"    name: grpc",
		`    endpoint: "127.0.0.1:19100"`,
		"    dataID: 1",
		"    connTimeout: 2s",
		`    path: "/tmp/probe-sandbox/logs/probe.log"`,
		"    level: debug",
		"    fileCount: 10",
	}
	for _, line := range wantLines {
		if !strings.Contains(got, line) {
			t.Errorf("patched yaml missing line: %s", line)
		}
	}
	if strings.Contains(got, "name: gse") {
		t.Fatal("patched yaml still has gse reporter")
	}
}
