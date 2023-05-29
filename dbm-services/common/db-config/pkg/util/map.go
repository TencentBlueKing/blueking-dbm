package util

// IsEmptyMap TODO
// is a map is nil or len = 0
func IsEmptyMap(m map[string]interface{}) bool {
	if m == nil {
		return true
	} else if len(m) == 0 {
		return true
	} else {
		return false
	}
}

// IsEmptyMapString TODO
func IsEmptyMapString(m map[string]string) bool {
	if m == nil {
		return true
	} else if len(m) == 0 {
		return true
	} else {
		return false
	}
}

// MapHasElement TODO
func MapHasElement(aMap map[string]string, elem string) bool {
	if _, ok := aMap[elem]; ok {
		return true
	} else {
		return false
	}
}

// MapMerge goc
// 合并两个 map，传入的 map 可为 nil
// 如果 2 个都是 nil，返回一个 0 元素的初始化 map
func MapMerge(toMap, fromMap map[string]string) map[string]string {
	if toMap == nil && fromMap == nil {
		return make(map[string]string)
	} else if toMap == nil {
		return fromMap
	} else if fromMap == nil {
		return toMap
	}
	for k, v := range fromMap {
		toMap[k] = v
	}
	return toMap
}

// MapCopy TODO
func MapCopy(fromMap map[string]interface{}) map[string]interface{} {
	newMap := make(map[string]interface{})
	for k, v := range fromMap {
		newMap[k] = v
	}
	return newMap
}
