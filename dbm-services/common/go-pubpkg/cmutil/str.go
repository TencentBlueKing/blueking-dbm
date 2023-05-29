package cmutil

import (
	"math/rand"
	"strings"
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
