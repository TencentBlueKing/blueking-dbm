package common

import (
	"testing"
)

func TestParseGetFcvJSON(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name    string
		in      string
		want    string
		wantErr bool
	}{
		{
			name: "nested version from JSON.stringify eval",
			in:   `{"featureCompatibilityVersion":{"version":"3.6"}}`,
			want: "3.6",
		},
		{
			name: "string form",
			in:   `{"featureCompatibilityVersion":"4.4"}`,
			want: "4.4",
		},
		{
			name: "plain version string from eval",
			in:   `"6.0"`,
			want: "6.0",
		},
		{
			name:    "shell style output with Timestamp is not valid JSON",
			in:      `{"featureCompatibilityVersion":{"version":"3.6"},"ok":1,"operationTime":Timestamp(1775183833,1)}`,
			wantErr: true,
		},
		{
			name:    "errmsg from failed query",
			in:      `{"errmsg":"not primary"}`,
			wantErr: true,
		},
		{
			name:    "empty version",
			in:      `{"featureCompatibilityVersion":{"version":""}}`,
			wantErr: true,
		},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got, err := ParseGetFcvJSON(tc.in)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got version %q", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got != tc.want {
				t.Fatalf("version: got %q, want %q", got, tc.want)
			}
		})
	}
}

func TestParseGetFcvJSON_TrimsWhitespace(t *testing.T) {
	t.Parallel()
	in := "\n  {\"featureCompatibilityVersion\":{\"version\":\"5.0\"}}  \n"
	got, err := ParseGetFcvJSON(in)
	if err != nil {
		t.Fatal(err)
	}
	if got != "5.0" {
		t.Fatalf("got %q", got)
	}
}

func TestParseGetFcvJSON_ShellOutputStartsWithInvalidToken(t *testing.T) {
	t.Parallel()
	// Typical output where warning/noise is printed before final JSON line
	in := "Type \"it\" for more\n{\"featureCompatibilityVersion\":{\"version\":\"4.2\"}}"
	got, err := ParseGetFcvJSON(in)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != "4.2" {
		t.Fatalf("got %q", got)
	}
}
