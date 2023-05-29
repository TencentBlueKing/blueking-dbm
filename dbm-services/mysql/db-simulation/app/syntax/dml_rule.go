package syntax

// Checker TODO
func (c DeleteResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	r.Parse(R.DmlRule.DmlNotHasWhere, c.HasWhere || c.Limit > 0, "")
	return
}

// Checker TODO
func (c UpdateResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	r.Parse(R.DmlRule.DmlNotHasWhere, c.HasWhere || c.Limit > 0, "")
	return
}
