package redisinfo

import (
	"fmt"
	"strconv"
	"strings"
)

type RedisVersion struct {
	Str                 string
	IsCommunityVersion  bool
	IsTredis            bool
	HasTFlag            bool
	TredisMainVersion   string // 1.2 or 1.3
	Major, Minor, Patch int64
}

func (v *RedisVersion) Compare(v2 *RedisVersion) int64 {
	if v.Major > v2.Major {
		return 1
	} else if v.Major < v2.Major {
		return -1
	}
	if v.Minor > v2.Minor {
		return 1
	} else if v.Minor < v2.Minor {
		return -1
	}
	if v.Patch > v2.Patch {
		return 1
	} else if v.Patch < v2.Patch {
		return -1
	}
	return 0
}

func ParseRedisVersion(ver string) (*RedisVersion, error) {
	var r RedisVersion
	r.Str = ver
	fs := strings.SplitN(ver, ".", 3)
	if len(fs) != 3 {
		return nil, fmt.Errorf("bad version: %s", ver)
	}
	var err error
	r.Major, err = strconv.ParseInt(fs[0], 10, 32)
	if err != nil {
		return nil, err
	}
	r.Minor, err = strconv.ParseInt(fs[1], 10, 32)
	if err != nil {
		return nil, err
	}

	r.Patch, err = strconv.ParseInt(fs[2], 10, 32)
	const TredisSubString = "-TRedis-v"
	const TendisPlusString = "-rocksdb-"
	if err == nil {
		r.IsCommunityVersion = true
		return &r, nil
	} else {
		patch := fs[2]
		if strings.Contains(patch, "-t-") {
			r.HasTFlag = true
			return &r, nil
		} else if strings.Contains(patch, TredisSubString) {
			r.IsTredis = true
			idx := strings.Index(patch, TredisSubString)
			patch = patch[idx+len(TredisSubString):]
			fs2 := strings.Split(patch, ".")
			if len(fs2) < 2 {
				return nil, fmt.Errorf("bad version %s", ver)
			}
			r.TredisMainVersion = fmt.Sprintf("%s.%s", fs2[0], fs2[1]) // 1.2 or 1.3
			return &r, nil
			// TendisPlus, 兼容4.0.9
		} else if strings.Contains(patch, TendisPlusString) {
			r.IsTredis = true
			r.TredisMainVersion = "4.0"
			return &r, nil
		} else {
			return nil, fmt.Errorf("bad version %s", ver)
		}
	}
}
