package pitr

import (
	"testing"
)

func TestV1(t *testing.T) {
	var tests = []struct {
		input string
		want  error
	}{
		{"mongodump-xxxaapp-xx-game-s5-FULL-1.1.1.1-27005-2018031304-20180313041134.tar.gz", nil},
		{"mongodump-xxxaapp-xx-game-s5-INCR-1.1.1.1-27005-2018031304-1-20180313051101.oplog.rs.bson.gz", nil},
		{"mongodump-v1-mongo-cyc-k8stest-db-shard0-2-INCR-1.1.1.1-27017-20191220100027-1-20191220102027-1-oplog.rs.bson.gz", nil},
		{"mongodump-v1-mongo-cyc-k8stest-db-shard0-2-FULL-1.1.1.1-27017-20191219195952-2.tar", nil},
		{"mongodump-v1-mongo-cyc-k8stest-db-shard0-2-0-FULL-1.1.1.1-27017-20191219195952-2.tar", nil},
	}

	for _, v := range tests {
		if filename, err := DecodeFilename(v.input); err != v.want {
			t.Errorf("ERR CheckInput (%q) return filename:%+verr:(%v)", v.input, filename, err)
		} else {
			t.Logf("OK CheckInput (%q) return filename:%+verr:(%v)", v.input, filename, err)
		}
	}
}
