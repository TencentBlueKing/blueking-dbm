package pitr

import (
	"github.com/pkg/errors"
	"testing"
)

func TestParseTimeStr(t *testing.T) {
	var tests = []struct {
		input string
		want  error
	}{
		{"2024-07-17T23:00:00+08:00", nil},
		{"2024-07-17T23:00:00-07:00", nil},
		{"2024-07-17T23:00:00Z07:00", errors.New("ParseTimeStr")},
		{"2024-07-17T23:00:00", nil},
	}

	for _, v := range tests {
		if out, err := ParseTimeStr(v.input); !errors.Is(err, v.want) {
			t.Errorf("ERR ParseTimeStr (%q) return out:%v err:(%v)", v.input, out, err)
		} else {
			t.Logf("OK ParseTimeStr (%q) return out:%v err:(%v)", v.input, out, err)
		}
	}
}
