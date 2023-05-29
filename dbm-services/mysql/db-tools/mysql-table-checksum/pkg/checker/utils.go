package checker

import "strings"

func rewritePattern(pattern string) string {
	return strings.Replace(
		strings.Replace(
			strings.Replace(
				strings.Replace(pattern, "%", ".*", -1),
				"?", ".", -1,
			),
			`\.*`, `\%`, -1,
		), `\.`, `\?`, -1,
	)
}
