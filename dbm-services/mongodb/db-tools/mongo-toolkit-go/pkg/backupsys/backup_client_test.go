package backupsys

import (
	"bytes"
	"testing"

	"github.com/stretchr/testify/assert"
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
		v, err := splitLines(buff)
		assert.NoError(t, err)
		assert.Equal(t, tt.wantValue, v[tt.wantKey])
		t.Logf("name: %s v: %v", tt.name, v)

	}

}
