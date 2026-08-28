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
	"fmt"
	"os"
	"strings"
)

func patchProbeYAML(path, receiverAddr, logPath string) error {
	raw, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	patched := patchProbeYAMLText(string(raw), receiverAddr, logPath)
	if err := os.WriteFile(path, []byte(patched), 0o644); err != nil {
		return err
	}
	fmt.Printf("patched reporter to grpc, path: %s, endpoint: %s\n", path, receiverAddr)
	return nil
}

func patchProbeYAMLText(text, receiverAddr, logPath string) string {
	lines := strings.Split(text, "\n")
	out := make([]string, 0, len(lines)+1)
	inReporter := false
	inLog := false
	inAdmin := false
	adminHasSync := false
	adminChildIndent := "  "

	flushAdminSync := func() {
		if !inAdmin || adminHasSync {
			return
		}
		out = append(out, adminChildIndent+"syncInterval: 0s")
		adminHasSync = true
	}

	for _, line := range lines {
		stripped := strings.TrimSpace(line)
		indent := line[:len(line)-len(strings.TrimLeft(line, " \t"))]
		switch {
		case strings.HasPrefix(line, "reporter:"):
			flushAdminSync()
			inReporter, inLog, inAdmin = true, false, false
			out = append(out, line)
		case strings.HasPrefix(line, "log:"):
			flushAdminSync()
			inLog, inReporter, inAdmin = true, false, false
			out = append(out, line)
		case strings.HasPrefix(line, "admin:"):
			inAdmin, inReporter, inLog = true, false, false
			adminHasSync = false
			out = append(out, line)
		case line != "" && !strings.HasPrefix(line, " ") && !strings.HasPrefix(line, "\t"):
			flushAdminSync()
			inReporter, inLog, inAdmin = false, false, false
			out = append(out, line)
		case inAdmin && strings.HasPrefix(stripped, "syncInterval:"):
			out = append(out, indent+"syncInterval: 0s")
			adminHasSync = true
			adminChildIndent = indent
		case inAdmin:
			if indent != "" {
				adminChildIndent = indent
			}
			out = append(out, line)
		case inReporter && strings.HasPrefix(stripped, "name:"):
			out = append(out, indent+"name: grpc")
		case inReporter && strings.HasPrefix(stripped, "endpoint:"):
			out = append(out, indent+`endpoint: "`+receiverAddr+`"`)
		case inLog && logPath != "" && strings.HasPrefix(stripped, "path:"):
			out = append(out, indent+`path: "`+logPath+`"`)
		case inLog && strings.HasPrefix(stripped, "level:"):
			out = append(out, indent+"level: debug")
		default:
			out = append(out, line)
		}
	}
	flushAdminSync()
	return strings.Join(out, "\n")
}
