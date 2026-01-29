package syntax

// SpiderRenameTableRule rename table checker
func (c RenameTableResult) SpiderChecker(spiderVersion string) (r *CheckerResult) {
	r = &CheckerResult{
		ObjName:   "",
		IsSQLText: true,
	}
	r.Parse(SR.RenameTableRule.MultipleRenamePairsNotAllowed, len(c.RenameTablePairs), SR.RenameTableRule.MultipleRenamePairsNotAllowed.Suggestion)
	return r
}
