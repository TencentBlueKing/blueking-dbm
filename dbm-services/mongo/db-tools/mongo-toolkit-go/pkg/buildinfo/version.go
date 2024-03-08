package buildinfo

import "fmt"

var version string
var githash string
var buildstamp string
var goversion string

func VersionInfo() string {
	return fmt.Sprintf(`Version: %s
Githash: %s
Buildstamp:%s
GoVersion: %s`, version, githash, buildstamp, goversion)
}

func VersionInfoOneLine() string {
	return fmt.Sprintf(`Version: %s Githash: %s Buildstamp:%s GoVersion: %s`, version, githash, buildstamp, goversion)
}
