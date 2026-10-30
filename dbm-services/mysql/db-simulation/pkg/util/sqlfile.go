package util

import (
	"fmt"
	"path/filepath"
	"strings"
	"unicode"
	"unicode/utf8"
)

// ValidateSQLFileName accepts a single filename, not a filesystem path.
func ValidateSQLFileName(name string) error {
	if name == "" || name == "." || name == ".." || !utf8.ValidString(name) ||
		strings.ContainsAny(name, `/\`) || strings.IndexFunc(name, unicode.IsControl) >= 0 {
		return fmt.Errorf("invalid SQL filename %q: expected a single filename without control characters", name)
	}
	return nil
}

// SQLFilePath resolves a filename inside a non-empty working directory.
func SQLFilePath(dir, name string) (string, error) {
	if err := ValidateSQLFileName(name); err != nil {
		return "", err
	}
	if dir == "" {
		return "", fmt.Errorf("SQL working directory is empty")
	}
	base, err := filepath.Abs(dir)
	if err != nil {
		return "", err
	}
	filePath := filepath.Join(base, name)
	rel, err := filepath.Rel(base, filePath)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) || filepath.IsAbs(rel) {
		return "", fmt.Errorf("SQL filename %q is outside the working directory", name)
	}
	return filePath, nil
}
