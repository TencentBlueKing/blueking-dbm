package common

import (
	"os"
	"regexp"
	"strings"
)

var tlinux4ReleaseRE = regexp.MustCompile(`(?i)(?:release|version_id=|version=)\s*"?4(?:\.|\s|"|$)`)
var tencentos4RE = regexp.MustCompile(`(?i)tencentos server\s+4`)

// IsTlinux4Text 判断发行版文本是否为 tlinux / TencentOS 4.x。
func IsTlinux4Text(text string) bool {
	lower := strings.ToLower(text)
	if !strings.Contains(lower, "tlinux") && !strings.Contains(lower, "tencentos") {
		return false
	}
	return tlinux4ReleaseRE.MatchString(text) || tencentos4RE.MatchString(text)
}

// IsTlinux4 读取本机发行版文件判断是否为 tlinux4。
func IsTlinux4() bool {
	var b strings.Builder
	for _, p := range []string{"/etc/tlinux-release", "/etc/os-release"} {
		content, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		b.Write(content)
		b.WriteByte('\n')
	}
	return IsTlinux4Text(b.String())
}
