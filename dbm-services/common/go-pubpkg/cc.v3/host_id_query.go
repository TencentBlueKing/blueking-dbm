package cc

// QueryHostId 根据主机IP、固资号查询主机信息
func QueryHostId(client *Client, innerIPs, aseetIds []string) ([]int, error) {
	var (
		hostIds []int
		lister  = NewHostWithoutBizList(client)
	)
	// 根据内网IP获取主机ID
	if len(innerIPs) > 0 {
		ret, err := lister.QueryWithFilter(HostPropertyFilter{
			Condition: "AND",
			Rules: []Rule{
				{
					Field:    "bk_host_innerip",
					Operator: "in",
					Value:    innerIPs,
				},
			},
		}, BKPage{
			Start: 0,
			Limit: Limit,
		})
		if err != nil {
			return nil, err
		}
		for _, item := range ret.Info {
			hostIds = append(hostIds, item.BKHostId)
		}
	}
	// 根据固资号获取主机ID
	if len(aseetIds) > 0 {
		ret, err := lister.QueryWithFilter(HostPropertyFilter{
			Condition: "AND",
			Rules: []Rule{
				{
					Field:    "bk_asset_id",
					Operator: "in",
					Value:    aseetIds,
				},
			},
		}, BKPage{
			Start: 0,
			Limit: Limit,
		})
		if err != nil {
			return nil, err
		}
		for _, item := range ret.Info {
			hostIds = append(hostIds, item.BKHostId)
		}
	}
	return hostIds, nil
}

// RemoveRepeatedHostId TODO
func RemoveRepeatedHostId(hostIds []int) []int {
	var (
		result  []int
		hostIdM = make(map[int]struct{})
	)
	for _, id := range hostIds {
		if _, ok := hostIdM[id]; !ok {
			hostIdM[id] = struct{}{}
			result = append(result, id)
		}
	}
	return result
}
