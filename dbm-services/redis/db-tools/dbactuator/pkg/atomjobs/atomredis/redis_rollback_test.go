package atomredis

import (
	"encoding/json"
	"testing"
)

func TestRollbackParamsWriteBuffer(t *testing.T) {
	for payload, want := range map[string]int{
		`{"dest_ip":"2.2.2.2"}`:                       0,
		`{"dest_ip":"2.2.2.2","write_buffer_mb":0}`:   0,
		`{"dest_ip":"2.2.2.2","write_buffer_mb":128}`: 128,
	} {
		var params RedisRollbackParams
		if err := json.Unmarshal([]byte(payload), &params); err != nil {
			t.Fatal(err)
		}
		if params.WriteBufferMB != want {
			t.Fatalf("%s: write_buffer_mb=%d, want %d", payload, params.WriteBufferMB, want)
		}
	}
}
