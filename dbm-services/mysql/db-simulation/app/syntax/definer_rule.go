package syntax

// DefinerBase TODO
type DefinerBase struct {
	ParseBase
	Definer UserHost `json:"definer,omitempty"`
}

// Checker TODO
func (c DefinerBase) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	emptydefiner := UserHost{}
	if c.Definer != emptydefiner {
		r.Parse(R.CreateTableRule.DefinerRule, c.Command, "")
	}
	return
}
