package mysqlutil

import (
	"regexp"
	"strings"
)

var (
	mysqlRegex           = regexp.MustCompile(`mysql.*-u\w+.*\s-p(\w+).*`)
	mysqlAdminRegex      = regexp.MustCompile(`mysqladmin.*-u\w+.*\s-p(\w+).*`)
	mysqlPasswordRegex   = regexp.MustCompile(`\s-p[^\s]+`)
	masterPasswordRegexp = regexp.MustCompile(`master_password="[^\s]*"`)
	identifyByRegex      = regexp.MustCompile(`identified by '[^\s]*'`)
	userPasswordRegex    = regexp.MustCompile(`\s-u\w+.*\s-p(\w+).*`)
	dsnRegex             = regexp.MustCompile(`\w+:[^\s]*@tcp\([^\s]+\)`)
	dsnPasswordRegex     = regexp.MustCompile(`:[^\s]*@tcp\(`)
)

// ClearSensitiveInformation clear sensitive information from input
func ClearSensitiveInformation(input string) string {
	output := RemoveMysqlCommandPassword(input)
	output = ClearMasterPasswordInSQL(output)
	output = RemoveMysqlAdminCommandPassword(output)
	output = ClearIdentifyByInSQL(output)
	output = RemovePasswordInDSN(output)
	return output
}

// ClearIdentifyByInSQL TODO
func ClearIdentifyByInSQL(input string) string {
	output := identifyByRegex.ReplaceAllString(input, `identified by 'xxxx'`)
	return output
}

// ClearIdentifyByInSQLs TODO
func ClearIdentifyByInSQLs(input []string) []string {
	output := make([]string, len(input))
	for i, s := range input {
		output[i] = identifyByRegex.ReplaceAllString(strings.ToLower(s), `identified by 'xxxx'`)
	}
	return output
}

// ClearMasterPasswordInSQL TODO
func ClearMasterPasswordInSQL(input string) string {
	output := masterPasswordRegexp.ReplaceAllString(input, `master_password="xxxx"`)
	return output
}

// RemoveMysqlCommandPassword replace password field
func RemoveMysqlCommandPassword(input string) string {
	return mysqlRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return mysqlPasswordRegex.ReplaceAllString(sub, " -pxxxx")
	})
}

// RemoveMysqlAdminCommandPassword replace password field
func RemoveMysqlAdminCommandPassword(input string) string {
	return mysqlAdminRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return mysqlPasswordRegex.ReplaceAllString(sub, " -pxxxx")
	})
}

// RemovePassword replace password in -u -p pattern
func RemovePassword(input string) string {
	return userPasswordRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return mysqlPasswordRegex.ReplaceAllString(sub, " -pxxxx")
	})
}

// RemovePasswordInDSN TODO
func RemovePasswordInDSN(input string) string {
	return dsnRegex.ReplaceAllStringFunc(input, func(sub string) string {
		return dsnPasswordRegex.ReplaceAllString(sub, `:xxxx@tcp\(`)
	})
}
