package util

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

func convertVersionToUint(version string) (total uint64, err error) {
	version = strings.TrimSpace(version)
	if version == "" {
		return 0, nil
	}
	list01 := strings.Split(version, ".")
	billion := ""
	thousand := ""
	single := ""
	if len(list01) == 0 {
		err = fmt.Errorf("version:%s format not correct", version)
		return 0, err
	}
	billion = list01[0]
	if len(list01) >= 2 {
		thousand = list01[1]
	}
	if len(list01) >= 3 {
		single = list01[2]
	}

	if billion != "" {
		b, err := strconv.ParseUint(billion, 10, 64)
		if err != nil {
			err = fmt.Errorf("convertVersionToUint strconv.ParseUint fail,err:%v,billion:%s,version:%s", err, billion, version)
			return 0, err
		}
		total += b * 1000000
	}
	if thousand != "" {
		t, err := strconv.ParseUint(thousand, 10, 64)
		if err != nil {
			err = fmt.Errorf("convertVersionToUint strconv.ParseUint fail,err:%v,thousand:%s,version:%s", err, thousand, version)
			return 0, err
		}
		total += t * 1000
	}
	if single != "" {
		s, err := strconv.ParseUint(single, 10, 64)
		if err != nil {
			err = fmt.Errorf("convertVersionToUint strconv.ParseUint fail,err:%v,single:%s,version:%s", err, single, version)
			return 0, err
		}
		total += s
	}
	return total, nil
}

// TendisVersionParse tendis版本解析
func TendisVersionParse(version string) (baseVersion, subVersion uint64, err error) {
	reg01 := regexp.MustCompile(`[\d+.]+`)
	rets := reg01.FindAllString(version, -1)
	if len(rets) == 0 {
		err = fmt.Errorf("TendisVersionParse version:%s format not correct", version)
		return 0, 0, err
	}
	if len(rets) >= 1 {
		baseVersion, err = convertVersionToUint(rets[0])
		if err != nil {
			return 0, 0, err
		}
	}
	if len(rets) >= 2 {
		subVersion, err = convertVersionToUint(rets[1])
		if err != nil {
			return 0, 0, err
		}
	}

	return baseVersion, subVersion, nil
}
