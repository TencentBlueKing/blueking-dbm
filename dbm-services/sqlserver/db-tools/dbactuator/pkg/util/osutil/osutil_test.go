package osutil_test

import (
	"fmt"
	"testing"
)

func TestIsFileExist(t *testing.T) {
	type test struct {
		b int
		a []string
	}
	a := test{b: 1}
	for _, i := range a.a {
		fmt.Println(i)
	}

}
