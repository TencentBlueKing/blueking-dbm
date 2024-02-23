package osutil_test

import (
	"fmt"
	"testing"

	"github.com/artdarek/go-unzip"
)

func TestIsFileExist(t *testing.T) {

	uz := unzip.New("/data/sysbench-1.0.20.zip", "/data/test")
	if err := uz.Extract(); err != nil {
		fmt.Println(err)
	}
}
