package util

import (
	"crypto/md5"
	"encoding/base64"
	"fmt"
	"io"
	"regexp"
	"strings"
)

// SplitInputs TODO
func SplitInputs(input string) []string {
	splitRegex := regexp.MustCompile(`[;,\n\t ]+`)
	splitResults := splitRegex.Split(input, -1)
	results := make([]string, 0)
	for _, s := range splitResults {
		if strings.TrimSpace(s) != "" {
			results = append(results, strings.TrimSpace(s))
		}
	}
	return results
}

// SplitAny TODO
// util.SplitAny("ab##cd$$ef", "(##|\$\$)")
func SplitAny(s string, delimiters string) []string {
	// seps := fmt.Sprintf()
	// splitRegex := regexp.MustCompile(`[;,\n\t ]+`)
	// delimiters=[;,\t\s ]+
	splitRegex := regexp.MustCompile(delimiters)
	splitResults := splitRegex.Split(s, -1)
	results := make([]string, 0)
	for _, s := range splitResults {
		if strings.TrimSpace(s) != "" {
			results = append(results, strings.TrimSpace(s))
		}
	}
	return results
}

// SplitAnyRune TODO
// util.SplitAnyRune("a,b c", ", ")
// if s is empty, return [], not [""]
func SplitAnyRune(s string, seps string) []string {
	splitter := func(r rune) bool {
		return strings.ContainsRune(seps, r)
	}
	return strings.FieldsFunc(s, splitter)
}

// SplitAnyRuneTrim godoc
func SplitAnyRuneTrim(s string, seps string) []string {
	ss := SplitAnyRune(s, seps)
	for i, el := range ss {
		ss[i] = strings.TrimSpace(el)
	}
	return ss
}

// ReplaceBlank 清楚字符串中的空格以及制表符
func ReplaceBlank(str string) string {
	if str == "" {
		return ""
	}
	// 匹配一个或多个空白符的正则表达式
	reg := regexp.MustCompile("\\s+")
	return reg.ReplaceAllString(str, "")
}

// SafeBase64Decode try base64 decode input, if failed, return input direct
func SafeBase64Decode(text string) string {
	bs, err := base64.StdEncoding.DecodeString(text)
	if err != nil {
		return text
	}
	return string(bs)
}

// Str2md5 TODO
func Str2md5(s string) string {
	w := md5.New()
	io.WriteString(w, s)
	md5str := fmt.Sprintf("%x", w.Sum(nil))
	return md5str
}
