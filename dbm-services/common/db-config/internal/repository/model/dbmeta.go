package model

// GetAppInfo TODO
// `/db_meta/db_module/query/{bk_biz_id}`
func GetAppInfo(bkBizID string) error {
	// return modules,clusters
	return nil
}

// GetModuleInfo TODO
func GetModuleInfo(bkBizID, module string) (string, error) {
	// return clusters,instances
	return "", nil
}

// GetClusterInfo TODO
// `/db_meta/cluster/query`
func GetClusterInfo(bkBizID, cluster string) (string, error) {
	// return module,instances
	return "", nil
}

// GetHostInfo TODO
func GetHostInfo(bkBizID, host string) (string, error) {
	// return modules,clusters,instances
	return "", nil
}

// GetInstanceInfo TODO
func GetInstanceInfo(bkBizID, instance string) (string, error) {
	// return module,host,cluster
	return "", nil
}
