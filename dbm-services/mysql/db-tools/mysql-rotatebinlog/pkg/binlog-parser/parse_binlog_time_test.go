package binlog_parser

import (
	"encoding/hex"
	"fmt"
	"os"
	"testing"

	"dbm-services/common/go-pubpkg/cmutil"

	"github.com/stretchr/testify/assert"
)

func TestGetTime(t *testing.T) {
	binlogContent := "fe62696eb1db64630f70003604890000008d00000000000400352e362e32342d746d7973716c2d322e322e322d6c6f670000000000000000000000000000000000000000000000000000000000000013380d0008001200040404041200007100041a08000000080808020000000a0a0a19190000000000000000000000000000000d0808080a0a0a0102311b69e1dc6463047000360431000000cdee1a010000040000000000000062696e6c6f6732303030302e333530363738776eb630"
	testFile := "/tmp/binlog_testfile.00001"
	b, err := hex.DecodeString(binlogContent)
	assert.Nil(t, err)
	cmutil.ExecShellCommand(false, fmt.Sprintf("rm -f %s", testFile))
	f, err := os.OpenFile(testFile, os.O_RDWR|os.O_CREATE, 644)
	assert.Nil(t, err)
	defer f.Close()
	_, err = f.Write(b)
	assert.Nil(t, err)

	// testFile = "./binlog20000.000002"
	binParse, _ := NewBinlogParse("mysql", 0, "")
	_, err = binParse.GetTime(testFile, true, true)
	assert.Nil(t, err)
	// fmt.Printf("%+v\n%+v\n", v[0], v[1])
}
