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
		{"mongodump-dba-theotest-FULL-1.1.1.1-27017-2025040116-20250401165507.tar.gz", nil},
		{"mongodump-dba-theotest-INCR-1.1.1.1-27017-2025040116-7-20250402000208-oplog.rs.bson", nil},
		{"mongodump-dba-theotest-FULL-1.1.1.1-27017-2025040116-20250401165507.archive", nil},
		{"mongodump-dba-theotest-FULL-1.1.1.1-27017-2025040116-20250401165507.archive.gz", nil},
		{"mongodump-dba-theotest-FULL-1.1.1.1-27017-2025040116-20250401165507.archive.zst", nil},
		{"mongodump-dba-theotest-FULL-1.1.1.1-27017-2025040116-20250401165507.archive.zstd", nil},
		{"mongodump-dba-theotest-INCR-1.1.1.1-27017-2025040116-7-20250402000208-oplog.rs.bson.zst", nil},
	}

	for _, v := range tests {
		if _, err := DecodeFilename(v.input); err != v.want {
			t.Errorf("ERR DecodeFilename (%q) return err:(%v)", v.input, err)
		} else {
			// t.Logf("OK DecodeFilename (%q) return filename: %+v", v.input, filename)
		}
	}
}
