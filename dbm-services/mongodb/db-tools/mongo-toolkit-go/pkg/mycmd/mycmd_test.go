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
		for _, vv := range v.args {
			cb.Append(v.cmd).Append(vv)
		}

		o, err := cb.Run2(5 * time.Second)
		t.Logf("cmd %s stdout %q stderr %q err %v",
			cb.GetCmdLine("", false), o.OutBuf.String(), o.ErrBuf.String(), err)
		if err != nil {
			t.Errorf("cmd %s err %v", cb.GetCmdLine("", false), err)
			continue
		}

	}

}
