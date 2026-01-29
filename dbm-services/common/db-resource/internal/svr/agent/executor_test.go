/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import (
	"strings"
	"testing"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/meta"
)

// TestFormatSubZoneIDsInText tests the FormatSubZoneIDsInText function
func TestFormatSubZoneIDsInText(t *testing.T) {
	// Setup: add some test entries to SubzoneIdMap
	originalMap := model.SubzoneIdMap
	model.SubzoneIdMap = map[string]string{
		"268":  "光明",
		"1109": "深宇",
		"500":  "南山",
	}
	defer func() { model.SubzoneIdMap = originalMap }()

	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "single zone id in text",
			input:    "园区268没有可用资源",
			expected: "园区光明(268)没有可用资源",
		},
		{
			name:     "multiple zone ids in text",
			input:    "园区268有2台，园区1109有0台",
			expected: "园区光明(268)有2台，园区深宇(1109)有0台",
		},
		{
			name:     "zone id without mapping",
			input:    "园区999没有可用资源",
			expected: "园区999没有可用资源",
		},
		{
			name:     "mixed mapped and unmapped ids",
			input:    "园区268有资源，园区999没有资源",
			expected: "园区光明(268)有资源，园区999没有资源",
		},
		{
			name:     "no zone id in text",
			input:    "这是一段普通文本",
			expected: "这是一段普通文本",
		},
		{
			name:     "empty input",
			input:    "",
			expected: "",
		},
		{
			name:     "complex sentence",
			input:    "申请指定的园区1109没有符合规格的可用资源。整个云区域中，只有园区268有2台符合设备规格",
			expected: "申请指定的园区深宇(1109)没有符合规格的可用资源。整个云区域中，只有园区光明(268)有2台符合设备规格",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatSubZoneIDsInText(tt.input)
			if result != tt.expected {
				t.Errorf("FormatSubZoneIDsInText(%q) = %q, expected %q",
					tt.input, result, tt.expected)
			}
		})
	}
}

// TestBuildUserMessageKeepsOriginalIDs tests that BuildUserMessage keeps the original zone IDs
// so that LLM can use them correctly for subsequent queries
func TestBuildUserMessageKeepsOriginalIDs(t *testing.T) {
	// Setup: add some test entries to SubzoneIdMap
	originalMap := model.SubzoneIdMap
	model.SubzoneIdMap = map[string]string{
		"268":  "光明",
		"1109": "深宇",
	}
	defer func() { model.SubzoneIdMap = originalMap }()

	params := &apply.RequestInputParam{
		ResourceType: "redis",
		Details: []apply.ObjectDetail{
			{
				Count: 2,
				LocationSpec: meta.LocationSpec{
					SubZoneIds: []string{"1109"},
				},
			},
		},
	}

	message := BuildUserMessage(params)

	// The message should contain the original zone ID "1109", NOT the translated name
	// This ensures LLM uses correct IDs for database queries
	if !strings.Contains(message, "\"1109\"") {
		t.Errorf("BuildUserMessage should contain original zone ID '1109', got: %s", message)
	}

	// The message should NOT contain translated format like "深宇(1109)"
	if strings.Contains(message, "深宇(1109)") {
		t.Errorf("BuildUserMessage should NOT contain translated zone name, got: %s", message)
	}

	// Verify original params are not modified
	if params.Details[0].LocationSpec.SubZoneIds[0] != "1109" {
		t.Errorf("Original params should not be modified, SubZoneIds[0] = %s, expected '1109'",
			params.Details[0].LocationSpec.SubZoneIds[0])
	}
}

// TestReplaceAll tests the replaceAll helper function
func TestReplaceAll(t *testing.T) {
	tests := []struct {
		name     string
		s        string
		old      string
		new      string
		expected string
	}{
		{
			name:     "single replacement",
			s:        "hello world",
			old:      "world",
			new:      "go",
			expected: "hello go",
		},
		{
			name:     "multiple replacements",
			s:        "foo bar foo baz foo",
			old:      "foo",
			new:      "qux",
			expected: "qux bar qux baz qux",
		},
		{
			name:     "no match",
			s:        "hello world",
			old:      "xyz",
			new:      "abc",
			expected: "hello world",
		},
		{
			name:     "empty old string",
			s:        "hello",
			old:      "",
			new:      "x",
			expected: "hello",
		},
		{
			name:     "same old and new",
			s:        "hello",
			old:      "l",
			new:      "l",
			expected: "hello",
		},
		{
			name:     "new contains old (should not loop infinitely)",
			s:        "268",
			old:      "268",
			new:      "光明(268)",
			expected: "光明(268)",
		},
		{
			name:     "new contains old multiple times",
			s:        "园区268 园区268",
			old:      "268",
			new:      "光明(268)",
			expected: "园区光明(268) 园区光明(268)",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := replaceAll(tt.s, tt.old, tt.new)
			if result != tt.expected {
				t.Errorf("replaceAll(%q, %q, %q) = %q, expected %q",
					tt.s, tt.old, tt.new, result, tt.expected)
			}
		})
	}
}

// TestIndexOf tests the indexOf helper function
func TestIndexOf(t *testing.T) {
	tests := []struct {
		name     string
		s        string
		substr   string
		expected int
	}{
		{
			name:     "found at start",
			s:        "hello world",
			substr:   "hello",
			expected: 0,
		},
		{
			name:     "found in middle",
			s:        "hello world",
			substr:   "o w",
			expected: 4,
		},
		{
			name:     "found at end",
			s:        "hello world",
			substr:   "world",
			expected: 6,
		},
		{
			name:     "not found",
			s:        "hello world",
			substr:   "xyz",
			expected: -1,
		},
		{
			name:     "empty substr",
			s:        "hello",
			substr:   "",
			expected: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := indexOf(tt.s, tt.substr)
			if result != tt.expected {
				t.Errorf("indexOf(%q, %q) = %d, expected %d",
					tt.s, tt.substr, result, tt.expected)
			}
		})
	}
}
