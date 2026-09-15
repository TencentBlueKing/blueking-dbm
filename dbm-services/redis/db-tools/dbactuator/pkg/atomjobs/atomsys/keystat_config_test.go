package atomsys

import (
	"fmt"
	"strings"
	"testing"
)

func TestParseConfigValue(t *testing.T) {
	tests := []struct {
		name       string
		result     any
		configName string
		want       string
		wantErr    string
	}{
		{
			name:       "maxmemory",
			result:     []any{"maxmemory", "4294967296"},
			configName: "maxmemory",
			want:       "4294967296",
		},
		{
			name:       "case insensitive name",
			result:     []any{"MAXMEMORY-POLICY", "volatile-lru"},
			configName: "maxmemory-policy",
			want:       "volatile-lru",
		},
		{
			name:       "missing value",
			result:     []any{"maxmemory"},
			configName: "maxmemory",
			wantErr:    "maxmemory not found",
		},
		{
			name:       "unexpected result type",
			result:     "maxmemory",
			configName: "maxmemory",
			wantErr:    "result is not []interface{}",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseConfigValue(tt.result, tt.configName)
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("parseConfigValue() error = %v, want error containing %q", err, tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("parseConfigValue() unexpected error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("parseConfigValue() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestIsLruMaxmemoryPolicy(t *testing.T) {
	tests := []struct {
		policy string
		want   bool
	}{
		{"volatile-lru", true},
		{"allkeys-lru", true},
		{"ALLKEYS-LRU", true},
		{" volatile-lru ", true},
		{"noeviction", false},
		{"allkeys-lfu", false},
		{"volatile-ttl", false},
		{"", false},
	}
	for _, tt := range tests {
		if got := isLruMaxmemoryPolicy(tt.policy); got != tt.want {
			t.Fatalf("isLruMaxmemoryPolicy(%q) = %v, want %v", tt.policy, got, tt.want)
		}
	}
}

func TestIsUnknownCommandErr(t *testing.T) {
	tests := []struct {
		err  error
		want bool
	}{
		{nil, false},
		{fmt.Errorf("ERR unknown command `confxx`"), true},
		{fmt.Errorf("ERR Unknown Command 'confxx'"), true},
		{fmt.Errorf("timeout"), false},
		{fmt.Errorf("NOAUTH Authentication required"), false},
	}
	for _, tt := range tests {
		if got := isUnknownCommandErr(tt.err); got != tt.want {
			t.Fatalf("isUnknownCommandErr(%v) = %v, want %v", tt.err, got, tt.want)
		}
	}
}
