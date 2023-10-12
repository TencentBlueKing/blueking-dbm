package syntax

import (
	"fmt"
)

// DefinerBase TODO
type DefinerBase struct {
	ParseBase
	Definer UserHost `json:"definer,omitempty"`
}

// Checker TODO
func (c DefinerBase) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	r.Parse(R.CreateTableRule.DefinerRule, fmt.Sprintf("%s@%s", c.Definer.User, c.Definer.Host), "")
	return
}
