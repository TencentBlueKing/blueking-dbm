package keystat_report

import (
	"testing"
)

func TestGetTtlHuman(t *testing.T) {
	tests := []struct {
		name     string
		input    int64
		expected string
	}{
		// 边界情况
		{
			name:     "zero seconds",
			input:    0,
			expected: "0sec",
		},
		{
			name:     "negative one (no expiration)",
			input:    -1,
			expected: "-",
		},
		// 秒级别
		{
			name:     "1 second",
			input:    1,
			expected: "1sec",
		},
		{
			name:     "59 seconds",
			input:    59,
			expected: "59sec",
		},
		// 小时级别
		{
			name:     "1 hour",
			input:    3600,
			expected: "1.0hour",
		},
		{
			name:     "2.5 hours",
			input:    9000,
			expected: "2.5hour",
		},
		{
			name:     "23 hours",
			input:    82800,
			expected: "23.0hour",
		},
		// 天级别
		{
			name:     "1 day",
			input:    86400,
			expected: "1.0day",
		},
		{
			name:     "2.5 days",
			input:    216000,
			expected: "2.5day",
		},
		{
			name:     "29 days",
			input:    2505600,
			expected: "29.0day",
		},
		// 月级别
		{
			name:     "1 month",
			input:    2592000,
			expected: "1.0mon",
		},
		{
			name:     "2.5 months",
			input:    6480000,
			expected: "2.5mon",
		},
		{
			name:     "11 months",
			input:    28512000,
			expected: "11.0mon",
		},
		// 年级别
		{
			name:     "1 year",
			input:    31536000,
			expected: "1.0year",
		},
		{
			name:     "2.5 years",
			input:    78840000,
			expected: "2.5year",
		},
		{
			name:     "10 years",
			input:    315360000,
			expected: "10.0year",
		},
		// 边界值测试
		{
			name:     "just below 1 hour",
			input:    3599,
			expected: "3599sec",
		},
		{
			name:     "just below 1 day",
			input:    86399,
			expected: "24.0hour",
		},
		{
			name:     "just below 1 month",
			input:    2591999,
			expected: "30.0day",
		},
		{
			name:     "just below 1 year",
			input:    31535999,
			expected: "12.2mon",
		},
		{
			name:     "1year 1 month and 1 day",
			input:    31536000 + 2592000 + 86400 + 43200 + 3600 + 60 + 1,
			expected: "1.1year",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := getTtlHuman(tt.input)
			if result != tt.expected {
				t.Errorf("getTtlHuman(%d) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}
