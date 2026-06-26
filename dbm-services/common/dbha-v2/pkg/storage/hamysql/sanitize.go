package hamysql

import (
	"regexp"
)

const (
	sanitizedSecret      = "<secret>"
	maxSanitizedErrorLen = 256
)

var (
	dsnFragmentPattern    = regexp.MustCompile(`[^\s]+:[^\s]+@(tcp|unix)\([^)]+\)[^\s]*`)
	dsnCredentialPattern  = regexp.MustCompile(`([^\s:/]+):([^@\s]+)@`)
	sensitiveParamPattern = regexp.MustCompile(`(?i)(password|token|passwd|pwd)\s*=\s*[^\s&]+`)
)

// SanitizeConnectionError returns a desensitized error summary safe for harvest reporting.
// Passwords, tokens, and DSN credential segments are redacted. MySQL error codes and server
// messages are preserved when they do not embed credentials. err may be nil.
func SanitizeConnectionError(err error) string {
	if err == nil {
		return ""
	}

	msg := err.Error()
	msg = dsnFragmentPattern.ReplaceAllString(msg, "<redacted-dsn>")
	msg = dsnCredentialPattern.ReplaceAllString(msg, "$1:"+sanitizedSecret+"@")
	msg = sensitiveParamPattern.ReplaceAllString(msg, "$1="+sanitizedSecret)

	if len(msg) > maxSanitizedErrorLen {
		msg = msg[:maxSanitizedErrorLen]
	}
	return msg
}
