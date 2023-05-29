package ext3check

import "strings"

// uniqueDirs TODO
/*
在某些情况下, mysql 的工作目录可能是这样子
datadir: /data/mysqldata/data
tmpdir: /data/mysqldata/data/tmp
如果不做去重, tmp会被扫描两遍
*/
func uniqueDirs(dirs []string) []string {
	if len(dirs) <= 1 {
		return dirs
	}

	for i, d := range dirs {
		for j, ld := range dirs {
			if i == j {
				continue
			}

			if strings.HasPrefix(d, ld) { // ld is base, replace d with ld
				dirs[i] = ld
				break
			}
			if strings.HasPrefix(ld, d) { // d is base, replace ld with d
				dirs[j] = d
				continue
			}
		}
	}
	um := make(map[string]int)
	for _, d := range dirs {
		um[d] = 1
	}

	var res []string
	for k := range um {
		res = append(res, k)
	}

	return res
}
