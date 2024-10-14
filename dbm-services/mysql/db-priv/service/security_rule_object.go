package service

import "time"

const BigDataRule = "{\"max_length\":32,\"min_length\":6,\"include_rule\":{\"numbers\":true,\"symbols\":false,\"lowercase\":true,\"uppercase\":true},\"number_of_types\":2,\"symbols_allowed\":\"\",\"weak_password\":false,\"repeats\":4}"
const MysqlSqlserverRule = "{\"max_length\":32,\"min_length\":6,\"include_rule\":{\"numbers\":true,\"symbols\":true,\"lowercase\":true,\"uppercase\":true},\"number_of_types\":2,\"symbols_allowed\":\"!#%&()*+,-./;<=>?[]^_{|}~@:$\",\"weak_password\":false,\"repeats\":4}"
const RedisRule = "{\"max_length\":32,\"min_length\":8,\"include_rule\":{\"numbers\":true,\"symbols\":true,\"lowercase\":true,\"uppercase\":true},\"number_of_types\":2,\"symbols_allowed\":\"#@%=+-;\",\"weak_password\":false,\"repeats\":4}"
const MongodbRule = "{\"max_length\":32,\"min_length\":8,\"include_rule\":{\"numbers\":true,\"symbols\":true,\"lowercase\":true,\"uppercase\":true},\"number_of_types\":2,\"symbols_allowed\":\"#%=+-;\",\"weak_password\":false,\"repeats\":4}"

// SecurityRulePara 安全规则相关函数的入参
type SecurityRulePara struct {
	Id       int64  `json:"id"`
	Name     string `json:"name"`
	Rule     string `json:"rule"`
	Operator string `json:"operator"`
	Reset    bool   `json:"reset"`
}

// TbSecurityRules 安全规则表
type TbSecurityRules struct {
	Id         int64     `gorm:"column:id;primary_key;auto_increment" json:"id"`
	Name       string    `gorm:"column:name;not_null" json:"name"`
	Rule       string    `gorm:"column:rule;not_null" json:"rule"`
	Creator    string    `gorm:"column:creator;not_null;" json:"creator"`
	CreateTime time.Time `gorm:"column:create_time" json:"create_time"`
	Operator   string    `gorm:"column:operator" json:"operator"`
	UpdateTime time.Time `gorm:"column:update_time" json:"update_time"`
}

// SecurityRule 安全规则
type SecurityRule struct {
	MaxLength      int         `json:"max_length"`      // 密码的最大长度
	MinLength      int         `json:"min_length"`      // 密码的最小长度
	IncludeRule    IncludeRule `json:"include_rule"`    // 密码组成
	NumberOfTypes  int         `json:"number_of_types"` // 包含任意多少种类型
	SymbolsAllowed string      `json:"symbols_allowed"` // 指定特殊字符
	WeakPassword   bool        `json:"weak_password"`   // 弱密码检查，连续N位的字母顺序、数字顺序、特殊符号顺序、键盘顺序、重复的字母、数字、特殊字符
	Repeats        int         `json:"repeats"`         // 连续N位
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
	NumberOfTypesValid   bool   `json:"number_of_types_valid"` // ”包含任意多少种类型“的检查结果
	AllowedValid         bool   `json:"allowed_valid"`         // 是否在允许的字符列表内
	OutOfRange           string `json:"out_of_range"`          // 不在允许列表的字符
	RepeatsValid         bool   `json:"repeats_valid"`
	FollowLettersValid   bool   `json:"follow_letters_valid"`
	FollowSymbolsValid   bool   `json:"follow_symbols_valid"`
	FollowKeyboardsValid bool   `json:"follow_keyboards_valid"`
	FollowNumbersValid   bool   `json:"follow_numbers_valid"`
	MinLengthValid       bool   `json:"min_length_valid"`
	MaxLengthValid       bool   `json:"max_length_valid"`
}
