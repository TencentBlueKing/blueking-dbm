package restore

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

func checkExistRunningDbLoad(db *native.DbWorker, checkProcess bool, dblist []string) (bool, []string, error) {
	// 检查进程
	if !checkProcess || len(dblist) == 0 {
		return true, nil, nil
	}

	processList, err := db.SelectProcesslist([]string{native.DBUserAdmin})
	if err != nil {
		return false, nil, err
	}
	if len(processList) == 0 {
		return true, nil, nil
	}

	var runningDbs []string
	for _, process := range processList {
		if !process.DB.Valid {
			continue
		}
		if util.StringsHas(dblist, process.DB.String) {
			runningDbs = append(runningDbs, process.DB.String)
		}
	}
	runningDbs = util.UniqueStrings(runningDbs)
	return true, runningDbs, nil
}
