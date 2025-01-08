package checker

import "slices"

var systemUsers []string

type Analyzer struct {
	deep              bool
	userPrivSummaries map[string]*userPrivSummary
}

func NewAnalyzer() *Analyzer {
	return &Analyzer{
		userPrivSummaries: make(map[string]*userPrivSummary),
	}
}

func init() {
	systemUsers = []string{
		"MONITOR",
		"gcs_admin",
		"gcs_dba",
		"GM",
		"gcs_spider",
	}
}

func IsSystemUser(userName string) bool {
	return slices.Index(systemUsers, userName) >= 0
}
