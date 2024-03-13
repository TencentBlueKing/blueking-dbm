package mycmd

import (
	"testing"
	"time"
)

func TestCmd(t *testing.T) {
	var input = []struct {
		cmd      string
		args     []string
		out, err string
	}{
		{"du", []string{"-sm", "/tmp"}, "0\t/tmp\n", ""},
	}
	for _, v := range input {
		cb := NewCmdBuilder()
		cb.Append(v.cmd).Append(v.args...)
		o, err := cb.Run2(5 * time.Second)
		if err != nil {
			t.Errorf("cmd %s err %v", cb.GetCmdLine("", false), err)
			continue
		}
		t.Logf("cmd %s stdout %q stderr %q err %v",
			cb.GetCmdLine("", false), o.OutBuf.String(), o.ErrBuf.String(), err)
	}

}
