package util

import (
	"regexp"
	"strings"
)

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
