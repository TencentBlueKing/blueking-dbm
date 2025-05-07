package cmutil

import (
	"math/rand"
	"strings"

	"github.com/spf13/cast"
)

// IsEmpty TODO
func IsEmpty(str string) bool {
	return strings.TrimSpace(str) == ""
}

// IsNotEmpty TODO
func IsNotEmpty(str string) bool {
	return !IsEmpty(str)
}

var letters = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

// RandStr TODO
func RandStr(n int) string {
	b := make([]rune, n)
	for i := range b {
		b[i] = letters[rand.Intn(len(letters))]
	}
	return string(b)
}

// SplitAnyRune TODO
// util.SplitAnyRune("a,b c", ", ")
// if s is empty, return [], not [”]
func SplitAnyRune(s string, seps string) []string {
	splitter := func(r rune) bool {
		return strings.ContainsRune(seps, r)
	}
	return strings.FieldsFunc(s, splitter)
}

// SplitAnyRuneTrim 分隔字符串，并去除空字符
func SplitAnyRuneTrim(s string, seps string) []string {
	ss := SplitAnyRune(s, seps)
	for i, el := range ss {
		if sss := strings.TrimSpace(el); sss != "" {
			ss[i] = sss
		}
		// 忽略空字符
	}
	return ss
}

// StringToInt trim left 0
func StringToInt(s string) int {
	s = strings.TrimLeft(s, "0")
	return cast.ToInt(s)
}

// SubStringPrefix 返回字符串的前n个字符
// 如果超过字符串长度，返回整个字符串
func SubStringPrefix(src string, start int, end int) string {
	//return lo.Substring(src, start, end)

	var r = []rune(src)
	length := len(r)
	if start <= 0 && end > length {
		return src
	}
	if start < 0 {
		start = 0
	}
	if start > end || start > length {
		return ""
	}
	return string(r[start:end])
}

// ICaseEqual 字符串忽略大小写比较
func ICaseEqual(str1, str2 string) bool {
	return strings.EqualFold(str1, str2)
}
