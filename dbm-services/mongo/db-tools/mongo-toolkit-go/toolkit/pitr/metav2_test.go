package pitr

import (
	"testing"
)

func TestOplogFile(t *testing.T) {
	var tests = []struct {
		input string
		want  error
	}{
		{"mongodump-AppName-xxx-s1-INCR-1.1.1.1-11111-2023041704-3-20230417070206.oplog.rs.bson.gz 1681682521|1 1681686122|1", nil},
		{"mongodump-AppName-xxx-s1-INCR-1.1.1.1-11111-2023042404-8-20230424120142-oplog.rs.bson.gz 1682305302|1 1682308902|1", nil},
	}

	for _, v := range tests {
		if filename, err := parseOplogPosLine(v.input); err != v.want {
			t.Errorf("ERR CheckInput (%q) return filename:%+verr:(%v)", v.input, filename, err)
		} else {
			t.Logf("OK CheckInput (%q) return filename:%+verr:(%v)", v.input, filename, err)
		}
	}
}

func TestNilMap(t *testing.T) {
	var m map[string]string
	if m == nil {
		t.Logf("m is nil")
	} else {
		t.Logf("m is not nil")
	}
}
