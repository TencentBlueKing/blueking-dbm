package handler_rpc

func findDuplicateAddresses(addresses []string) []string {
	m := make(map[string]int)
	for _, address := range addresses {
		if _, exist := m[address]; !exist {
			m[address] = 1
			continue
		}
		m[address] += 1
	}

	var dup []string
	for address, count := range m {
		if count > 1 {
			dup = append(dup, address)
		}
	}

	return dup
}
