// Package buildinfo . 从go build中写入的版本信息
package buildinfo

import "fmt"

var version string
var githash string
var buildstamp string
var goversion string

// VersionInfo  return version info
func VersionInfo() string {
	return fmt.Sprintf(`Version: %s
Githash: %s
Buildstamp:%s
GoVersion: %s`, version, githash, buildstamp, goversion)
}

// VersionInfoOneLine return version info in one line
func VersionInfoOneLine() string {
	return fmt.Sprintf(`Version: %s Githash: %s Buildstamp:%s GoVersion: %s`, version, githash, buildstamp, goversion)
}
