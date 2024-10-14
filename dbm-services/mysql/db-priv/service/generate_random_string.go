package service

import (
	"fmt"
	"log/slog"
	"math/rand"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"
)

const lowercase = "abcdefghijklmnopqrstuvwxyz"
const uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
const number = "0123456789"

// 为密码池添加连续的字母序，数字序，特殊字符序和键盘序
const continuousSymbols = "~!@#$%^&*()_+"

var continuousKeyboardCol = []string{"1qaz", "2wsx", "3edc", "4rfv", "5tgb", "6yhn", "7ujm", "8ik,", "9ol.", "0p;/"}
var continuousKeyboardRow = []string{"qwertyuiop[]\\", "asdfghjkl;'", "zxcvbnm,./", "1234567890-="}

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
	var length int
	length = security.MaxLength
	var str []byte
	var vrange string
	rand.Seed(time.Now().UnixNano())
	symbol := security.SymbolsAllowed
	if security.IncludeRule.Lowercase {
		index := rand.Intn(len(lowercase))
		str = append(str, lowercase[index])
		vrange = fmt.Sprintf("%s%s", vrange, lowercase)
	}
	if security.IncludeRule.Uppercase {
		index := rand.Intn(len(uppercase))
		str = append(str, uppercase[index])
		vrange = fmt.Sprintf("%s%s", vrange, uppercase)
	}
	if security.IncludeRule.Symbols {
		index := rand.Intn(len(symbol))
		str = append(str, symbol[index])
		vrange = fmt.Sprintf("%s%s", vrange, symbol)
	}
	if security.IncludeRule.Numbers {
		index := rand.Intn(len(number))
		str = append(str, number[index])
		vrange = fmt.Sprintf("%s%s", vrange, number)
	}
	if len(str) > security.MinLength {
		return string(str), errno.IncludeCharTypesLargerThanLength
	}
	remain := length - len(str)
	if remain <= 0 {
		return string(str), nil
	}
	// 不要求包含任何字符
	if len(vrange) == 0 {
		vrange = fmt.Sprintf("%s%s%s%s", lowercase, uppercase, symbol, number)
	}

	//遍历，生成一个随机index索引
	for i := 0; i < remain; i++ {
		index := rand.Intn(len(vrange))
		str = append(str, vrange[index])
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
		true, "", true, true, true,
		true, true, true, true}}
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
	// 包含的字符类型
	var numberTypes int
	// 允许的字符范围
	var allCharAllowed string
	if security.IncludeRule.Lowercase {
		allCharAllowed = fmt.Sprintf("%s%s", allCharAllowed, lowercase)
		if CheckStringChar(password, lowercase) {
			numberTypes++
		}
	}
	if security.IncludeRule.Uppercase {
		allCharAllowed = fmt.Sprintf("%s%s", allCharAllowed, uppercase)
		if CheckStringChar(password, uppercase) {
			numberTypes++
		}
	}
	if security.IncludeRule.Numbers {
		allCharAllowed = fmt.Sprintf("%s%s", allCharAllowed, number)
		if CheckStringChar(password, number) {
			numberTypes++
		}
	}
	if security.IncludeRule.Symbols {
		allCharAllowed = fmt.Sprintf("%s%s", allCharAllowed, security.SymbolsAllowed)
		if CheckStringChar(password, security.SymbolsAllowed) {
			numberTypes++
		}
	}
	if numberTypes < security.NumberOfTypes {
		check.PasswordVerifyInfo.NumberOfTypesValid = false
		check.IsStrength = false
	}
	// 超过范围的字符
	var outOfRange string
	for _, item := range password {
		s := string(item)
		if !strings.Contains(allCharAllowed, s) {
			outOfRange = fmt.Sprintf("%s%s", outOfRange, s)
		}
	}
	if outOfRange != "" {
		check.PasswordVerifyInfo.AllowedValid = false
		check.PasswordVerifyInfo.OutOfRange = outOfRange
		check.IsStrength = false
	}
	if security.WeakPassword {
		// 不能密码连续重复出现某字符
		if !CheckContinuousRepeats(str, security.Repeats) {
			check.PasswordVerifyInfo.RepeatsValid = false
			check.IsStrength = false
		}
		// 不能包含连续的某些字符(不区分大小写）
		if FindLongestCommonSubstr(strLower, lowercase) >= security.Repeats {
			check.PasswordVerifyInfo.FollowLettersValid = false
			check.IsStrength = false
		}
		if FindLongestCommonSubstr(strLower, number) >= security.Repeats {
			check.PasswordVerifyInfo.FollowNumbersValid = false
			check.IsStrength = false
		}
		if FindLongestCommonSubstr(strLower, continuousSymbols) >= security.Repeats {
			check.PasswordVerifyInfo.FollowSymbolsValid = false
			check.IsStrength = false
		}
		// 不能连续的键盘序
		keyboard := append(continuousKeyboardRow, continuousKeyboardCol...)
		for _, v := range keyboard {
			if FindLongestCommonSubstr(strLower, v) >= security.Repeats {
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
	var vmax int
	temp := make([][]int, len(s1)+1)
	for i := range temp {
		temp[i] = make([]int, len(s2)+1)
	}
	for i := 0; i < len(s1); i++ {
		for j := 0; j < len(s2); j++ {
			if s1[i] == s2[j] {
				temp[i+1][j+1] = temp[i][j] + 1
				if temp[i+1][j+1] > vmax {
					vmax = temp[i+1][j+1]
				}
			}
		}
	}
	return vmax
}

// CheckContinuousRepeats 字符连续重复出现的次数
func CheckContinuousRepeats(str string, repeats int) bool {
	str = strings.ToLower(str)
	var vmax, j int
	cnt := 1
	for i := 1; i < len(str); i++ {
		if str[i] == str[j] {
			cnt++
		}
		if str[i] != str[j] || i == len(str)-1 {
			if cnt > vmax {
				vmax = cnt
			}
			j = i
			cnt = 1
		}
	}
	return vmax < repeats
}

// CheckStringChar 字符串是否包含字符数组中的某个字符
func CheckStringChar(str []byte, charRange string) bool {
	for _, item := range str {
		if strings.Contains(charRange, string(item)) {
			return true
		}
	}
	return false
}
