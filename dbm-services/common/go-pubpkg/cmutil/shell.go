package cmutil

import "strings"

// ShellQuote protects a single argument from shell expansion.
func ShellQuote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}
