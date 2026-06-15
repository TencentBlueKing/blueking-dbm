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

package handler

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/tools/internal/bwmgr"
)

func TestWriteListOutputTable(t *testing.T) {
	t.Parallel()

	var output bytes.Buffer
	if err := writeListOutput(&output, testListItems(), ListOptions{}); err != nil {
		t.Fatalf("write list output failed: %s", err)
	}

	got := output.String()
	for _, want := range []string{"ID", "BK_BIZ_ID", "CLUSTER_NAME", "cluster-a", "2026-06-15T01:02:03Z"} {
		if !strings.Contains(got, want) {
			t.Fatalf("table output = %q, want contains %q", got, want)
		}
	}
}

func TestWriteListOutputJSON(t *testing.T) {
	t.Parallel()

	var output bytes.Buffer
	if err := writeListOutput(&output, testListItems(), ListOptions{Output: OutputFormatJSON}); err != nil {
		t.Fatalf("write list output failed: %s", err)
	}

	got := strings.TrimSpace(output.String())
	if !strings.Contains(got, "\n  {") {
		t.Fatalf("json output = %q, want indented json", got)
	}

	var decoded []bwmgr.BlackWhiteListItem
	if err := json.Unmarshal([]byte(got), &decoded); err != nil {
		t.Fatalf("unmarshal json output failed: %s", err)
	}
	if len(decoded) != len(testListItems()) {
		t.Fatalf("json item count = %d, want %d", len(decoded), len(testListItems()))
	}
}

func TestWriteListOutputFileWritesJSONLines(t *testing.T) {
	t.Parallel()

	var stdout bytes.Buffer
	outputFile := filepath.Join(t.TempDir(), "list.jsonl")
	opts := ListOptions{Output: "yaml", OutputFile: outputFile}
	if err := writeListOutput(&stdout, testListItems(), opts); err != nil {
		t.Fatalf("write list output failed: %s", err)
	}
	if stdout.Len() != 0 {
		t.Fatalf("stdout = %q, want empty output for file mode", stdout.String())
	}

	content, err := os.ReadFile(outputFile)
	if err != nil {
		t.Fatalf("read output file failed: %s", err)
	}

	got := string(content)
	if strings.HasPrefix(got, "[") {
		t.Fatalf("file output = %q, want json lines instead of json array", got)
	}

	lines := strings.Split(strings.TrimSuffix(got, "\n"), "\n")
	if len(lines) != len(testListItems()) {
		t.Fatalf("json lines count = %d, want %d", len(lines), len(testListItems()))
	}
	for _, line := range lines {
		if !json.Valid([]byte(line)) || !strings.HasPrefix(line, "{") {
			t.Fatalf("json line = %q, want a compact json object", line)
		}
	}
}

func TestWriteListOutputFileEmptyList(t *testing.T) {
	t.Parallel()

	outputFile := filepath.Join(t.TempDir(), "empty.jsonl")
	opts := ListOptions{OutputFile: outputFile}
	if err := writeListOutput(io.Discard, nil, opts); err != nil {
		t.Fatalf("write list output failed: %s", err)
	}

	content, err := os.ReadFile(outputFile)
	if err != nil {
		t.Fatalf("read output file failed: %s", err)
	}
	if len(content) != 0 {
		t.Fatalf("empty file output = %q, want empty content", string(content))
	}
}

func TestWriteListOutputInvalidOptions(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name string
		opts ListOptions
	}{
		{
			name: "invalid output",
			opts: ListOptions{Output: "yaml"},
		},
	}

	for _, tc := range tests {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			if err := writeListOutput(io.Discard, testListItems(), tc.opts); err == nil {
				t.Fatalf("write list output succeeded, want error")
			}
		})
	}
}

func testListItems() []bwmgr.BlackWhiteListItem {
	createdAt := time.Date(2026, time.June, 15, 1, 2, 3, 0, time.UTC)
	updatedAt := time.Date(2026, time.June, 15, 4, 5, 6, 0, time.UTC)

	return []bwmgr.BlackWhiteListItem{
		{
			ID:            1,
			BkBizID:       100,
			BkCloudID:     0,
			ClusterID:     200,
			ClusterName:   "cluster-a",
			SwitchVersion: bwmgr.SwitchVersionV2,
			Status:        bwmgr.StatusEnabled,
			CreatedAt:     createdAt,
			UpdatedAt:     updatedAt,
		},
		{
			ID:            2,
			BkBizID:       101,
			BkCloudID:     3,
			ClusterID:     201,
			ClusterName:   "cluster-b",
			SwitchVersion: bwmgr.SwitchVersionV1,
			Status:        bwmgr.StatusDisabled,
			CreatedAt:     createdAt,
			UpdatedAt:     updatedAt,
		},
	}
}
