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
