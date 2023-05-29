package backupsys

import (
	"bytes"
	"testing"
)

func Test_splitLines(t *testing.T) {

	tests := []struct {
		name      string
		args      string
		wantKey   string
		wantValue string
		wantErr   bool
	}{
		{
			name:      "test1",
			args:      "sending task......\nsend up backup task success!\r\ntaskid:15561723066\r\naaa",
			wantKey:   "taskid",
			wantValue: "15561723066",
			wantErr:   false,
		},
		{
			name:      "test2",
			args:      "UploadFile failed failed, stdout:sending task......\r\nsend up backup task success!\r\ntaskid:15561912052\r\n, stderr:",
			wantKey:   "taskid",
			wantValue: "15561912052",
			wantErr:   false,
		},
	}

	// splitLines(buffer bytes.Buffer) (map[string]string, error)
	for _, tt := range tests {
		buff := bytes.NewBufferString(tt.args)
		v, err := splitLines(*buff)
		t.Logf("name: %s v: err: %v", tt.name, err)
		for k, vv := range v {
			t.Logf("k: %q v: %q", k, vv)
		}
	}

}
