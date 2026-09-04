package model

import "testing"

func TestJSONQueryJoinQuotesMountPoint(t *testing.T) {
	cases := map[string][]string{
		`$."/data"`:           {"/data"},
		`$."/data".size`:      {"/data", "size"},
		`$."/data".disk_type`: {"/data", "disk_type"},
		`$."cpu"`:             {"cpu"},
	}
	for want, keys := range cases {
		if got := jsonQueryJoin(keys); got != want {
			t.Errorf("jsonQueryJoin(%v)=%q, want %q", keys, got, want)
		}
	}
}
