package util

import "strings"

// SplitLines splits a string into lines.
func SplitLines(s string) []string {
	return strings.Split(s, "\n")
}
