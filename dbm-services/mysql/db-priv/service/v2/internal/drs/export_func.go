package drs

func RPCMySQL(
	bkCloudId int64, addresses, cmds []string, force bool, timeout int64,
) ([]*OneAddressResult, error) {
	return dc.rpc(
		"/v2/mysql/rpc/",
		&drsRequest{
			Addresses:    addresses,
			Cmds:         cmds,
			Force:        force,
			QueryTimeout: timeout,
			BkCloudId:    bkCloudId,
		},
	)
}

func RPCProxyAdmin(
	bkCloudId int64, addresses, cmds []string, force bool, timeout int64,
) ([]*OneAddressResult, error) {
	return dc.rpc(
		"/v2/proxy-admin/rpc/",
		&drsRequest{
			Addresses:    addresses,
			Cmds:         cmds,
			Force:        force,
			QueryTimeout: timeout,
			BkCloudId:    bkCloudId,
		},
	)
}
