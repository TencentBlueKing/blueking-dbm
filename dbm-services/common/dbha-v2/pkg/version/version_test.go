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

package version

import (
	"bytes"
	"io"
	"os"
	"strings"
	"testing"
)

func TestPrint(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	Print("test-service")

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	io.Copy(&buf, r)
	output := buf.String()

	if !strings.Contains(output, "test-service") {
		t.Errorf("Print() output should contain service name, got: %s", output)
	}

	expectedLabels := []string{"BuildTime:", "GitTag:", "GitHash:", "Version:"}
	for _, label := range expectedLabels {
		if !strings.Contains(output, label) {
			t.Errorf("Print() output should contain %s, got: %s", label, output)
		}
	}
}

func TestPrintWithEmptyService(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	Print("")

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	io.Copy(&buf, r)
	output := buf.String()

	if !strings.Contains(output, "BuildTime:") {
		t.Errorf("Print() should work with empty service name, got: %s", output)
	}
}

func TestPackageVariables(t *testing.T) {
	if buildTime != "" {
		t.Logf("buildTime has value: %s (set via ldflags)", buildTime)
	}
	if gitTag != "" {
		t.Logf("gitTag has value: %s (set via ldflags)", gitTag)
	}
	if gitHash != "" {
		t.Logf("gitHash has value: %s (set via ldflags)", gitHash)
	}
	if version != "" {
		t.Logf("version has value: %s (set via ldflags)", version)
	}
}

func TestGet(t *testing.T) {
	info := Get()
	if info.BuildTime != buildTime {
		t.Errorf("Get().BuildTime = %q, want %q", info.BuildTime, buildTime)
	}
	if info.GitTag != gitTag {
		t.Errorf("Get().GitTag = %q, want %q", info.GitTag, gitTag)
	}
	if info.GitHash != gitHash {
		t.Errorf("Get().GitHash = %q, want %q", info.GitHash, gitHash)
	}
	if info.Version != version {
		t.Errorf("Get().Version = %q, want %q", info.Version, version)
	}
}

func TestPrintOutputFormat(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	Print("my-app")

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	io.Copy(&buf, r)
	output := buf.String()

	lines := strings.Split(strings.TrimSpace(output), "\n")

	if len(lines) != 5 {
		t.Errorf("Print() should output 5 lines, got %d: %v", len(lines), lines)
	}

	if lines[0] != "my-app" {
		t.Errorf("First line should be service name, got: %s", lines[0])
	}

	for i := 1; i < len(lines); i++ {
		if !strings.HasPrefix(lines[i], "\t") {
			t.Errorf("Line %d should start with tab, got: %s", i+1, lines[i])
		}
	}
}
