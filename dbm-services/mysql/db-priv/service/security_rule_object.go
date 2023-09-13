package service

import "dbm-services/mysql/priv-service/util"

// SecurityRulePara 安全规则相关函数的入参
type SecurityRulePara struct {
	Id       int64  `json:"id"`
	Name     string `json:"name"`
	Rule     string `json:"rule"`
	Operator string `json:"operator"`
}

// TbSecurityRules 安全规则表
type TbSecurityRules struct {
	Id         int64           `gorm:"column:id;primary_key;auto_increment" json:"id"`
	Name       string          `gorm:"column:name;not_null" json:"name"`
	Rule       string          `gorm:"column:rule;not_null" json:"rule"`
	Creator    string          `gorm:"column:creator;not_null;" json:"creator"`
	CreateTime util.TimeFormat `gorm:"column:create_time" json:"create_time"`
	Operator   string          `gorm:"column:operator" json:"operator"`
	UpdateTime util.TimeFormat `gorm:"column:update_time" json:"update_time"`
}

// SecurityRule 安全规则
type SecurityRule struct {
	ExcludeContinuousRule ExcludeContinuousRule `json:"exclude_continuous_rule"` // 连续字符的规则
	IncludeRule           IncludeRule           `json:"include_rule"`            // 密码中必须包含某些字符
	MaxLength             int                   `json:"max_length"`              // 密码的最大长度
	MinLength             int                   `json:"min_length"`              // 密码的最小长度
}

// ExcludeContinuousRule 密码不允许连续N位出现
type ExcludeContinuousRule struct {
	Limit     int  `json:"limit"`     //连续N位
	Letters   bool `json:"letters"`   //字母顺序
	Numbers   bool `json:"numbers"`   //数字顺序
	Symbols   bool `json:"symbols"`   //特殊符号顺序
	Keyboards bool `json:"keyboards"` //键盘顺序
	Repeats   bool `json:"repeats"`   //重复的字母、数字、特殊字符
}

type IncludeRule struct {
	Numbers   bool `json:"numbers"`   //是否包含数字
	Symbols   bool `json:"symbols"`   //是否包含字符
	Lowercase bool `json:"lowercase"` //是否包含小写
	Uppercase bool `json:"uppercase"` //是否包含大写
}

type CheckPasswordComplexity struct {
	IsStrength         bool               `json:"is_strength"`
	PasswordVerifyInfo PasswordVerifyInfo `json:"password_verify_info"`
}

type PasswordVerifyInfo struct {
	LowercaseValid       bool `json:"lowercase_valid"`
	UppercaseValid       bool `json:"uppercase_valid"`
	NumbersValid         bool `json:"numbers_valid"`
	SymbolsValid         bool `json:"symbols_valid"`
	RepeatsValid         bool `json:"repeats_valid"`
	FollowLettersValid   bool `json:"follow_letters_valid"`
	FollowSymbolsValid   bool `json:"follow_symbols_valid"`
	FollowKeyboardsValid bool `json:"follow_keyboards_valid"`
	FollowNumbersValid   bool `json:"follow_numbers_valid"`
	MinLengthValid       bool `json:"min_length_valid"`
	MaxLengthValid       bool `json:"max_length_valid"`
}
