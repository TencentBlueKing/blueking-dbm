package checker

import (
	"fmt"
	"regexp"
	"strings"
)

func FindPatternCover(sid []string) (res [][]string) {
	for i := 0; i < len(sid)-1; i++ {
		for j := i + 1; j < len(sid); j++ {
			if coverEachOther(sid[i], sid[j]) {
				res = append(res, []string{sid[i], sid[j]})
			}
		}
	}
	return res
}

func coverEachOther(a, b string) bool {
	return pCover(a, b) || pCover(b, a)
}

func pCover(a, b string) bool {
	a = strings.Replace(a, "*", `\*`, -1)
	a = strings.Replace(a, ".", `\.`, -1)
	a = strings.Replace(a, "%", ".*", -1)
	a = strings.Replace(a, "_", ".", -1)
	return regexp.MustCompile(fmt.Sprintf(`^%s$`, a)).MatchString(b)
}

func intersectStringSlice(s0, s1 []string) (res []string) {
	cache := make(map[string]int)
	for _, s := range append(s0, s1...) {
		if _, ok := cache[s]; !ok {
			cache[s] = 0
		}
		cache[s] += 1
	}

	for k, v := range cache {
		if v > 1 {
			res = append(res, k)
		}
	}
	return res
}
