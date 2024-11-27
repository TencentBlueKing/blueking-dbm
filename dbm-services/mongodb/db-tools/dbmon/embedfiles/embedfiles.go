// Package embedfiles mongodb javascript files
package embedfiles

import (
	// anonymous import package
	// import embed files
	_ "embed"
	"os"
)

// MongoLoginJs MongodDB Login JS
//
//go:embed  js/login-js
var MongoLoginJs string

func init() {
	// 为了import os包。 如果没有一个额外的import os 而直接 import _ "embed" . preci会报错
	os.Getpid()
}
