package backupclient

import "regexp"

var hdfsReg = regexp.MustCompile("^\\d+$")
var cosReg = regexp.MustCompile(`^\d+\-\d+.*`)

// IsHdfsTaskId if id is hdfs like task id format, return true
// 如果是国内HDFS，taskid 是数字类型，不会包含-
func IsHdfsTaskId(id string) bool {
	return hdfsReg.MatchString(id)
}

// IsCosTaskId if id is cos like task id format, return true
func IsCosTaskId(id string) bool {
	return cosReg.MatchString(id)
}
