package mysql_errlog

func spiderWarn() (string, error) {
	return scanSnapShot(nameSpiderErrWarn, spiderWarnPattern)
}
