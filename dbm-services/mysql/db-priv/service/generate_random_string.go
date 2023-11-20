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
const symbol = `!#$%&()*+,-./:;<=>?@[]^_{|}~` // 剔除 " ' ` \

// 为密码池添加连续的字母序，数字序，特殊字符序和键盘序
const continuousSymbols = "~!@#$%^&*()_+"

var continuousKeyboardCol = []string{"1qaz", "2wsx", "3edc", "4rfv", "5tgb", "6yhn", "7ujm", "8ik,", "9ol.", "0p;/"}
var continuousKeyboardRow = []string{"qwertyuiop[]\\", "asdfghjkl;'", "zxcvbnm,./"}

// GenerateRandomStringPara 生成随机字符串的函数的入参
type GenerateRandomStringPara struct {
	SecurityRuleName string `json:"security_rule_name"`
}

// CheckPasswordPara 检查密复杂度
type CheckPasswordPara struct {
	SecurityRuleName string `json:"security_rule_name"`
	Password         string `json:"password"`
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
		// 连续规则以及重复规则不通过，打乱顺序
		result := CheckPassword(security, str)
		if result.IsStrength {
			return string(str), nil
		}
	}
	slog.Error("error", errno.TryTooManyTimes.AddBefore("GenerateRandomString"))
	return "", errno.TryTooManyTimes.AddBefore("GenerateRandomString")
}

func CheckPassword(security SecurityRule, password []byte) CheckPasswordComplexity {
	check := CheckPasswordComplexity{IsStrength: true, PasswordVerifyInfo: PasswordVerifyInfo{true,
		true, true, true, true, true,
		true, true, true, true, true}}
	str := string(password)
	strLower := strings.ToLower(str)
	// check 默认每个检查项是true，检查不通过是false
	if len(password) > security.MaxLength {
		check.PasswordVerifyInfo.MaxLengthValid = false
		check.IsStrength = false
	}
	if len(password) < security.MinLength {
		check.PasswordVerifyInfo.MinLengthValid = false
		check.IsStrength = false
	}
	// 必须包含某些字符
	if security.IncludeRule.Lowercase && !CheckStringChar(password, lowercase) {
		check.PasswordVerifyInfo.LowercaseValid = false
		check.IsStrength = false
	}
	if security.IncludeRule.Uppercase && !CheckStringChar(password, uppercase) {
		check.PasswordVerifyInfo.UppercaseValid = false
		check.IsStrength = false
	}
	if security.IncludeRule.Numbers && !CheckStringChar(password, number) {
		check.PasswordVerifyInfo.NumbersValid = false
		check.IsStrength = false
	}
	if security.IncludeRule.Symbols && !CheckStringChar(password, symbol) {
		check.PasswordVerifyInfo.SymbolsValid = false
		check.IsStrength = false
	}

	excludeContinuous := security.ExcludeContinuousRule
	// 不能密码连续重复出现某字符
	if excludeContinuous.Repeats && !CheckContinuousRepeats(
		str, excludeContinuous.Limit) {
		check.PasswordVerifyInfo.RepeatsValid = false
		check.IsStrength = false
	}
	// 不能包含连续的某些字符(不区分大小写）
	if excludeContinuous.Letters && FindLongestCommonSubstr(strLower, lowercase) >= excludeContinuous.Limit {
		check.PasswordVerifyInfo.FollowLettersValid = false
		check.IsStrength = false
	}
	if excludeContinuous.Numbers && FindLongestCommonSubstr(strLower, number) >= excludeContinuous.Limit {
		check.PasswordVerifyInfo.FollowNumbersValid = false
		check.IsStrength = false
	}
	if excludeContinuous.Symbols && FindLongestCommonSubstr(strLower, continuousSymbols) >= excludeContinuous.Limit {
		check.PasswordVerifyInfo.FollowSymbolsValid = false
		check.IsStrength = false
	}
	// 不能连续的键盘序
	if excludeContinuous.Keyboards {
		keyboard := append(continuousKeyboardRow, continuousKeyboardCol...)
		for _, v := range keyboard {
			if FindLongestCommonSubstr(strLower, v) >= excludeContinuous.Limit {
				check.PasswordVerifyInfo.FollowKeyboardsValid = false
				check.IsStrength = false
				break
			}
		}
	}
	return check
}

// RandShuffle 随机打乱字符串中的字符顺序
func RandShuffle(slice *[]byte) {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	r.Shuffle(len(*slice), func(i, j int) {
		(*slice)[i], (*slice)[j] = (*slice)[j], (*slice)[i]
	})
}

// FindLongestCommonSubstr 找出最长的公共字符串子串以及其长度
func FindLongestCommonSubstr(s1, s2 string) int {
	var max int
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
				}
			}
		}
	}
	return max
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

func CheckStringChar(str []byte, charRange string) bool {
	for _, item := range str {
		if strings.Contains(charRange, string(item)) {
			return true
		}
	}
	return false
}
