package atommongodb

import "testing"

func TestVersionMajorMinor(t *testing.T) {
	t.Parallel()
	cases := []struct {
		in   string
		want string
	}{
		{"mongodb-3.0", "3.0"},
		{"3.2.10", "3.2"},
		{"mongodb-6.0.27", "6.0"},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.in, func(t *testing.T) {
			t.Parallel()
			if got := versionMajorMinor(tc.in); got != tc.want {
				t.Fatalf("got %q, want %q", got, tc.want)
			}
		})
	}
}
