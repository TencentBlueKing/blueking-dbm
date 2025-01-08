package checker

const (
	PrivErrorHostConflict            = "host_conflict"
	PrivErrorDBConflict              = "db_conflict"
	PrivErrorPasswordNotMatch        = "password_not_match"
	PrivErrorWithGrantOptionNotMatch = "with_grant_option_not_match"
	PrivErrorGrantToDifferentDB      = "grant_to_different_db"
	PrivErrorGrantToDifferentTable   = "grant_to_different_table"
	PrivErrorPrivilegesNotMatch      = "privileges_not_match"
)

type PrivErrorInfo struct {
	ErrorType string `json:"error_type"`
	Object1   string `json:"object1"`
	Object2   string `json:"object2"`
	Msg       string `json:"msg"`
}

func (c *Analyzer) Check(deep bool) (res []*PrivErrorInfo) {
	c.deep = deep
	for userName, userSummary := range c.userPrivSummaries {
		if !IsSystemUser(userName) {
			res = append(res, c.checkUser(userSummary)...)
		}
	}

	return res
}
