package mysql_errlog

func spiderCritical() (string, error) {
	return scanSnapShot(nameSpiderErrCritical, spiderCriticalPattern)
}
