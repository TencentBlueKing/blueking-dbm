package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"fmt"
	"math"
	"math/rand"
	"strings"
	"time"

	"golang.org/x/exp/slog"
)

const lowercase = "abcdefghijklmnopqrstuvwxyz"
const uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
const number = "0123456789"
const symbol = `!#$%&()*+,-./:;<=>?@[\]^_{|}~`

// 为密码池添加连续的字母序，数字序，特殊字符序和键盘序
const continuousSymbols = "~!@#$%^&*()_+"

var continuousKeyboardCol = []string{"1qaz", "2wsx", "3edc", "4rfv", "5tgb", "6yhn", "7ujm", "8ik,", "9ol.", "0p;/"}
var continuousKeyboardRow = []string{"qwertyuiop[]\\", "asdfghjkl;'", "zxcvbnm,./"}

// GenerateRandomStringPara 生成随机字符串的函数的入参
type GenerateRandomStringPara struct {
	SecurityRuleName string `json:"security_rule_name"`
}

func GenerateRandomString(security SecurityRule) (string, error) {
	length := rand.Intn(security.MaxLength-security.MinLength) + security.MinLength
	var str []byte
	// 字母与数字占比90%，符号占比10%
	alphabetNumberStr := fmt.Sprintf("%s%s%s", lowercase, uppercase, number)
	alphabetNumberPercent := 0.9
	rand.Seed(time.Now().UnixNano())
	// 必须包含的字符，至少有一个
	if security.IncludeRule.Lowercase {
		index := rand.Intn(len(lowercase))
		str = append(str, lowercase[index])
	}
	if security.IncludeRule.Uppercase {
		index := rand.Intn(len(uppercase))
		str = append(str, uppercase[index])
	}
	if security.IncludeRule.Symbols {
		index := rand.Intn(len(symbol))
		str = append(str, symbol[index])
	}
	if security.IncludeRule.Numbers {
		index := rand.Intn(len(number))
		str = append(str, number[index])
	}
	if len(str) > security.MinLength {
		return string(str), errno.IncludeCharTypesLargerThanLength
	}
	remain := length - len(str)
	if remain <= 0 {
		return string(str), nil
	}
	alphabetNumberCnt := int(math.Ceil(alphabetNumberPercent * float64(remain)))
	symbolCnt := remain - alphabetNumberCnt
	//遍历，生成一个随机index索引
	for i := 0; i < alphabetNumberCnt; i++ {
		index := rand.Intn(len(alphabetNumberStr))
		str = append(str, alphabetNumberStr[index])
	}
	for i := 0; i < symbolCnt; i++ {
		index := rand.Intn(len(symbol))
		str = append(str, symbol[index])
	}
	for i := 0; i < 10; i++ {
		RandShuffle(&str)
		repeatOk := security.ExcludeContinuousRule.Repeats &&
			CheckContinuousRepeats(string(str), security.ExcludeContinuousRule.Limit) ||
			security.ExcludeContinuousRule.Repeats == false
		// 连续规则以及重复规则不通过，打乱顺序
		if CheckExcludeContinuousRule(string(str), security.ExcludeContinuousRule) && repeatOk {
			return string(str), nil
		}
	}
	slog.Error("error", errno.TryTooManyTimes.AddBefore("GenerateRandomString"))
	return "", errno.TryTooManyTimes.AddBefore("GenerateRandomString")
}

// RandShuffle 随机打乱字符串中的字符顺序
func RandShuffle(slice *[]byte) {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	r.Shuffle(len(*slice), func(i, j int) {
		(*slice)[i], (*slice)[j] = (*slice)[j], (*slice)[i]
	})
}

// CheckExcludeContinuousRule 检查密码不允许连续N位出现某个规则
func CheckExcludeContinuousRule(str string, rule ExcludeContinuousRule) bool {
	str = strings.ToLower(str)
	// 连续的符号或者数字或者字母
	if rule.Symbols {
		_, cnt := FindLongestCommonSubstr(str, continuousSymbols)
		if cnt >= rule.Limit {
			return false
		}
	}
	if rule.Numbers {
		_, cnt := FindLongestCommonSubstr(str, number)
		if cnt >= rule.Limit {
			return false
		}
	}
	if rule.Letters {
		_, cnt := FindLongestCommonSubstr(str, lowercase)
		if cnt >= rule.Limit {
			return false
		}
	}
	// 连续的键盘序
	if rule.Keyboards {
		for _, v := range continuousKeyboardRow {
			_, cnt := FindLongestCommonSubstr(str, v)
			if cnt >= rule.Limit {
				return false
			}
		}
		for _, v := range continuousKeyboardCol {
			_, cnt := FindLongestCommonSubstr(str, v)
			if cnt >= rule.Limit {
				return false
			}
		}
	}
	return true
}

// FindLongestCommonSubstr 找出最长的公共字符串子串以及其长度
func FindLongestCommonSubstr(s1, s2 string) (string, int) {
	var max, pos int
	temp := make([][]int, len(s1)+1)
	for i := range temp {
		temp[i] = make([]int, len(s2)+1)
	}
	for i := 0; i < len(s1); i++ {
		for j := 0; j < len(s2); j++ {
			if s1[i] == s2[j] {
				temp[i+1][j+1] = temp[i][j] + 1
				if temp[i+1][j+1] > max {
					max = temp[i+1][j+1]
					pos = i + 1
				}
			}
		}
	}
	return s1[pos-max : pos], max
}

// CheckContinuousRepeats 字符连续重复出现的次数
func CheckContinuousRepeats(str string, repeats int) bool {
	str = strings.ToLower(str)
	var max, j int
	cnt := 1
	for i := 1; i < len(str); i++ {
		if str[i] == str[j] {
			cnt++
		}
		if str[i] != str[j] || i == len(str)-1 {
			if cnt > max {
				max = cnt
			}
			j = i
			cnt = 1
		}
	}
	return max < repeats
}
