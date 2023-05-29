package entity

import "strings"

// IsNoRowFoundError TODO
func IsNoRowFoundError(err error) bool {
	if err == nil {
		return false
	}

	if strings.Contains(err.Error(), "no row found") {
		return true
	}
	return false
}
