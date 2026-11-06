/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmutil_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/go-pubpkg/cmutil"
)

const (
	versionFormat = "%s 版本: %s"
	failFormat    = "%s 版本探测失败: %s"
	emptyPathText = "版本探测失败，二进制路径为空"
)

type logCall struct {
	format string
	args   []interface{}
}

func logSink(dst *[]logCall) func(string, ...interface{}) {
	return func(format string, args ...interface{}) {
		copied := make([]interface{}, len(args))
		copy(copied, args)
		*dst = append(*dst, logCall{format: format, args: copied})
	}
}

func writeFakeBin(t *testing.T, body string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "fake-bin")
	if err := os.WriteFile(path, []byte(body), 0o755); err != nil {
		t.Fatal(err)
	}
	return path
}

func assertNoSecret(t *testing.T, calls []logCall) {
	t.Helper()
	for _, call := range calls {
		if strings.Contains(call.format, "-p") || strings.Contains(call.format, "password") {
			t.Fatalf("format contains a secret marker: %q", call.format)
		}
		for _, arg := range call.args {
			text, ok := arg.(string)
			if !ok {
				continue
			}
			if strings.Contains(text, "-p") || strings.Contains(text, "password") {
				t.Fatalf("arg contains a secret marker: %q", text)
			}
		}
	}
}

func TestLogBinaryVersionSuccess(t *testing.T) {
	bin := writeFakeBin(t, "#!/bin/sh\necho 'mydumper 0.1.2-test'\n")
	var infoCalls, warnCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&warnCalls))
	if len(infoCalls) != 1 {
		t.Fatalf("info calls = %d, want 1", len(infoCalls))
	}
	if infoCalls[0].format != versionFormat {
		t.Fatalf("format = %q", infoCalls[0].format)
	}
	if len(infoCalls[0].args) != 2 || infoCalls[0].args[0] != bin || infoCalls[0].args[1] != "mydumper 0.1.2-test" {
		t.Fatalf("args = %#v", infoCalls[0].args)
	}
	if len(warnCalls) != 0 {
		t.Fatalf("warn calls = %#v", warnCalls)
	}
	assertNoSecret(t, infoCalls)
}

func TestLogBinaryVersionStderrOnly(t *testing.T) {
	bin := writeFakeBin(t, "#!/bin/sh\necho 'mydumper 0.1.2-test' >&2\n")
	var infoCalls, warnCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&warnCalls))
	if len(warnCalls) != 0 {
		t.Fatalf("warn calls = %#v", warnCalls)
	}
	if len(infoCalls) != 1 || infoCalls[0].format != versionFormat {
		t.Fatalf("info calls = %#v", infoCalls)
	}
	if len(infoCalls[0].args) != 2 || infoCalls[0].args[1] != "mydumper 0.1.2-test" {
		t.Fatalf("args = %#v", infoCalls[0].args)
	}
}

func TestLogBinaryVersionNonZeroExit(t *testing.T) {
	bin := writeFakeBin(t, "#!/bin/sh\necho 'library not found' >&2\nexit 1\n")
	var infoCalls, warnCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&warnCalls))
	if len(infoCalls) != 0 {
		t.Fatalf("info calls = %#v", infoCalls)
	}
	if len(warnCalls) != 1 {
		t.Fatalf("warn calls = %d, want 1", len(warnCalls))
	}
	if warnCalls[0].format != failFormat {
		t.Fatalf("format = %q", warnCalls[0].format)
	}
	if len(warnCalls[0].args) != 2 || warnCalls[0].args[0] != bin {
		t.Fatalf("args = %#v", warnCalls[0].args)
	}
	reason, _ := warnCalls[0].args[1].(string)
	if reason != "exit status 1: library not found" {
		t.Fatalf("reason = %q", reason)
	}
}

func TestLogBinaryVersionArgv(t *testing.T) {
	dir := t.TempDir()
	argvPath := filepath.Join(dir, "argv.txt")
	bin := filepath.Join(dir, "fake-bin")
	body := "#!/bin/sh\nprintf '%s\\n' \"$0\" \"$@\" > '" + argvPath + "'\necho 'mydumper 0.1.2-test'\n"
	if err := os.WriteFile(bin, []byte(body), 0o755); err != nil {
		t.Fatal(err)
	}
	var infoCalls, warnCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&warnCalls))
	raw, err := os.ReadFile(argvPath)
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimRight(string(raw), "\n"), "\n")
	if len(lines) != 2 || lines[0] != bin || lines[1] != "--version" {
		t.Fatalf("argv = %#v", lines)
	}
	assertNoSecret(t, append(append([]logCall{}, infoCalls...), warnCalls...))
}

func TestLogBinaryVersionPercent(t *testing.T) {
	bin := writeFakeBin(t, "#!/bin/sh\nprintf '%s\\n' '100%'\n")
	var infoCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&[]logCall{}))
	if len(infoCalls) != 1 {
		t.Fatalf("info calls = %#v", infoCalls)
	}
	if infoCalls[0].format != versionFormat {
		t.Fatalf("format = %q", infoCalls[0].format)
	}
	if len(infoCalls[0].args) != 2 || infoCalls[0].args[1] != "100%" {
		t.Fatalf("args = %#v", infoCalls[0].args)
	}
}

func TestLogBinaryVersionLibraryPath(t *testing.T) {
	t.Setenv("LD_LIBRARY_PATH", "libmydumper-test")
	bin := writeFakeBin(t, "#!/bin/sh\nprintf '%s\\n' \"$LD_LIBRARY_PATH\"\n")
	var infoCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&[]logCall{}))
	if len(infoCalls) != 1 || len(infoCalls[0].args) != 2 {
		t.Fatalf("info calls = %#v", infoCalls)
	}
	text, _ := infoCalls[0].args[1].(string)
	if !strings.Contains(text, "libmydumper-test") {
		t.Fatalf("logged line = %q", text)
	}
	if got := os.Getenv("LD_LIBRARY_PATH"); got != "libmydumper-test" {
		t.Fatalf("process LD_LIBRARY_PATH = %q", got)
	}
}

func TestLogBinaryVersionMissing(t *testing.T) {
	bin := filepath.Join(t.TempDir(), "missing-bin")
	var infoCalls, warnCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&warnCalls))
	if len(infoCalls) != 0 {
		t.Fatalf("info calls = %#v", infoCalls)
	}
	if len(warnCalls) != 1 || warnCalls[0].format != failFormat {
		t.Fatalf("warn calls = %#v", warnCalls)
	}
}

func TestLogBinaryVersionNilWarn(t *testing.T) {
	bin := writeFakeBin(t, "#!/bin/sh\necho 'library not found' >&2\nexit 1\n")
	var infoCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), nil)
	if len(infoCalls) != 0 {
		t.Fatalf("info calls = %#v", infoCalls)
	}
}

func TestLogBinaryVersionTwice(t *testing.T) {
	bin := writeFakeBin(t, "#!/bin/sh\necho 'mydumper 0.1.2-test'\n")
	var infoCalls []logCall
	sink := logSink(&infoCalls)
	cmutil.LogBinaryVersion(bin, sink, logSink(&[]logCall{}))
	cmutil.LogBinaryVersion(bin, sink, logSink(&[]logCall{}))
	if len(infoCalls) != 2 {
		t.Fatalf("info calls = %d, want 2", len(infoCalls))
	}
	if infoCalls[0].format != versionFormat || infoCalls[1].format != versionFormat {
		t.Fatalf("formats = %q %q", infoCalls[0].format, infoCalls[1].format)
	}
	if infoCalls[0].args[1] != "mydumper 0.1.2-test" || infoCalls[1].args[1] != infoCalls[0].args[1] {
		t.Fatalf("args = %#v %#v", infoCalls[0].args, infoCalls[1].args)
	}
}

func TestLogBinaryVersionMultiline(t *testing.T) {
	bin := writeFakeBin(t, "#!/bin/sh\nprintf '%s\\n\\n%s\\n' '  mydumper 0.1.2-test  ' 'ignored-second'\n")
	var infoCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&[]logCall{}))
	if len(infoCalls) != 1 || len(infoCalls[0].args) != 2 {
		t.Fatalf("info calls = %#v", infoCalls)
	}
	if infoCalls[0].args[1] != "mydumper 0.1.2-test" {
		t.Fatalf("line = %#v", infoCalls[0].args[1])
	}
}

func TestLogBinaryVersionEmptyPath(t *testing.T) {
	var warnCalls []logCall
	cmutil.LogBinaryVersion("", logSink(&[]logCall{}), logSink(&warnCalls))
	if len(warnCalls) != 1 || warnCalls[0].format != emptyPathText || len(warnCalls[0].args) != 0 {
		t.Fatalf("warn calls = %#v", warnCalls)
	}
	cmutil.LogBinaryVersion("", nil, nil)
}

func TestLogBinaryVersionCapRune(t *testing.T) {
	line := strings.Repeat("a", 298) + "中" + "tail"
	bin := writeFakeBin(t, "#!/bin/sh\nprintf '%s\\n' '"+line+"'\n")
	var infoCalls []logCall
	cmutil.LogBinaryVersion(bin, logSink(&infoCalls), logSink(&[]logCall{}))
	if len(infoCalls) != 1 || len(infoCalls[0].args) != 2 {
		t.Fatalf("info calls = %#v", infoCalls)
	}
	text, _ := infoCalls[0].args[1].(string)
	if text != strings.Repeat("a", 298) {
		t.Fatalf("capped = %q len=%d", text, len(text))
	}
}
