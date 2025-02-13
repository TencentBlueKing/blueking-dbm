package checker

import (
	"slices"

	"golang.org/x/time/rate"
)

var systemUsers []string
var limiter *rate.Limiter

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

	limiter = rate.NewLimiter(20, 1)
}

func IsSystemUser(userName string) bool {
	return slices.Index(systemUsers, userName) >= 0
}
