package logparserjob

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGetLastRotate(t *testing.T) {
	mongoFilePath := "/tmp/abc/xx.log"
	dir := filepath.Dir(mongoFilePath)
	tmpFile := filepath.Join(dir, ".last_rotate")
	os.Remove(tmpFile)
	_, err := os.Stat(tmpFile)
	t.Logf("tmpFile %s err: %v isNotExists: %v", tmpFile, err, os.IsNotExist(err))
	if err == nil {
		os.Remove(tmpFile)
	}
	got := getLastRotate(mongoFilePath)
	if got != -1 {
		t.Errorf("getLastRotate() = %v; want 0", got)
	} else {
		t.Log("TestGetLastRotate passed")
	}

}
