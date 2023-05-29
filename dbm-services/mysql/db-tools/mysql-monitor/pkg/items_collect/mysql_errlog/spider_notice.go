package mysql_errlog

func spiderNotice() (string, error) {
	return scanSnapShot(nameSpiderErrNotice, spiderNoticePattern)
}
