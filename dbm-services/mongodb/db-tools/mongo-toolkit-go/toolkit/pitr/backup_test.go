package pitr

import (
	"bytes"
	"testing"
)

func TestParseTs(t *testing.T) {
	var input1 = `2019-12-17T18:01:40.883+0800	firstTS=(1576576891 1)
2019-12-17T18:01:40.883+0800	lastTS=(1576576892 234)
lastTS(1576576893 2345)
`
	var buf = bytes.NewBuffer([]byte(input1))
	first, last, err := ParseTs(*buf)
	if err != nil {
		t.Errorf("first %+v second %+v err %v", first, last, err)
	}
	if first.Sec != 1576576891 || first.I != 1 ||
		last.Sec != 1576576892 || last.I != 234 {
		t.Errorf("first %+v second %+v err %v", first, last, err)
	}
	t.Logf("first %+v second %+v err %v", first, last, err)
}
