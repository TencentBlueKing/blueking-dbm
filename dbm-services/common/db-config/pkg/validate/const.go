package validate

import "regexp"

const (
	// RegexRangeStr 正则 (0, 2] 匹配上下边界，不限制为数字
	RegexRangeStr = `^([\(\[])(.+),(.+)([\)\]])$`
)

var regexRange = regexp.MustCompile(RegexRangeStr)

const (
	// DTypeString TODO
	DTypeString = "STRING"
	// DTypeInt TODO
	DTypeInt = "INT"
	// DTypeFloat TODO
	DTypeFloat = "FLOAT"
	// DTypeNumber TODO
	DTypeNumber = "NUMBER"
	// DTypeBool TODO
	DTypeBool = "BOOL"

	// DTypeSubString 普通任意string
	DTypeSubString = "STRING"
	// DTypeSubEmpty 空字符
	DTypeSubEmpty = ""
	// DTypeSubEnum 枚举类型，单值
	DTypeSubEnum = "ENUM"
	// DTypeSubEnums 枚举类型，多值
	DTypeSubEnums = "ENUMS"
	// DTypeSubRange 范围，支持开闭区间
	DTypeSubRange = "RANGE"
	// DTypeSubBytes 特殊的RANGE, range范围是数字[1024, 2048]，但值可以是 1M
	DTypeSubBytes = "BYTES"
	// DTypeSubRegex 正则
	DTypeSubRegex = "REGEX"
	// DTypeSubJson json 类型
	DTypeSubJson = "JSON"
	// DTypeSubMap 特殊的 json 类型, strict 模式下会转换成 map 返回
	DTypeSubMap = "MAP"
	// DTypeSubList list 类型，字符串。只影响数据返回格式，不检查写入
	DTypeSubList = "LIST"
	// DTypeSubDuration 时间间隔, 比如 1d2h3m1s
	DTypeSubDuration = "DURATION"
	// DTypeSubGovalidate TODO
	DTypeSubGovalidate = "GOVALIDATE"
	// DTypeSubFlag BOOL FLAG
	DTypeSubFlag = "FLAG"
)

// ValueTypeSubRef 定义合法的 value_type 与 value_type_sub 的关系
// value_type_sub 会用于控件展示、合法性校验
var ValueTypeSubRef = map[string][]string{
	DTypeString: []string{DTypeSubEmpty, DTypeSubString, DTypeSubEnum, DTypeSubEnums, DTypeSubBytes, DTypeSubRegex,
		DTypeSubJson, DTypeSubMap, DTypeSubDuration, DTypeSubGovalidate, DTypeSubList}, // 暂不支持复杂类型，比如 (1, 100] || on|off
	DTypeInt:    []string{DTypeSubEnum, DTypeSubEmpty, DTypeSubRange},
	DTypeFloat:  []string{DTypeSubEnum, DTypeSubEmpty, DTypeSubRange},
	DTypeNumber: []string{DTypeSubEnum, DTypeSubEmpty, DTypeSubRange},
	DTypeBool:   []string{DTypeSubEnum, DTypeSubEmpty, DTypeSubFlag},
}
