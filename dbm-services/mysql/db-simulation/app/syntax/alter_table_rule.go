package syntax

import util "dbm-services/common/go-pubpkg/cmutil"

// Checker TODO
func (c AlterTableResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	for _, altercmd := range c.AlterCommands {
		r.Parse(R.AlterTableRule.HighRiskType, altercmd.Type, "")
		r.Parse(R.AlterTableRule.HighRiskPkAlterType, altercmd.GetPkAlterType(), "")
		r.Parse(R.AlterTableRule.AlterUseAfter, altercmd.After, "")
	}
	r.Parse(R.AlterTableRule.AddColumnMixed, c.GetAllAlterType(), "")
	return
}

// GetAllAlterType TODO
// 对于 `alter table add a int(11),drop b,add d int(11);`
// 这种语句，我们需要把 alter type
// 也就是 add,drop,add 提取出来
// 去重后得到所有的alter types
func (c AlterTableResult) GetAllAlterType() (alterTypes []string) {
	for _, a := range c.AlterCommands {
		if !util.StringsHas([]string{"algorithm", "lock"}, a.Type) {
			alterTypes = append(alterTypes, a.Type)
		}
	}
	return util.RemoveDuplicate(alterTypes)
}

// GetPkAlterType  get the primary key change type
//
//	@receiver a
func (a AlterCommand) GetPkAlterType() string {
	if a.ColDef.PrimaryKey {
		return a.Type
	}
	return ""
}

// GetAlterAlgorithm TODO
//
//	@receiver a
func (a AlterCommand) GetAlterAlgorithm() string {
	return a.Algorithm
}
