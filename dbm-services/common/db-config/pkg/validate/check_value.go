package validate

import (
	"bk-dbconfig/pkg/util"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/go-playground/locales/en"
	ut "github.com/go-playground/universal-translator"
	"github.com/go-playground/validator/v10"
	en_translations "github.com/go-playground/validator/v10/translations/en"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// ValueTypeDef TODO
type ValueTypeDef struct {
	ValueType    string
	ValueTypeSub string
}

// Validate TODO
func (v *ValueTypeDef) Validate() error {
	return CheckDataTypeSub(v.ValueType, v.ValueTypeSub)
}

// ParseExprEnums 解析枚举类型，可以 |, 两种符号任意一种分隔
// 如果枚举值前后有空格，需要用 'a '|' b'| 这样单引号
func ParseExprEnums(enumStr string) ([]string, error) {
	enums := util.SplitAnyRune(enumStr, "|,")
	var enumsNew []string
	for _, e := range enums {
		// if e == ""
		enumsNew = append(enumsNew, strings.TrimSpace(e))
	}
	return enumsNew, nil
}

// ParseRange 解析范围格式
// 会把值转换成 float32, 返回 (['(', ']', ['0', '10'], err)
func ParseRange(rangeValue string) ([]string, []string, error) {
	rangeValue = strings.ReplaceAll(rangeValue, " ", "")
	matchAllowed := regexRange.FindStringSubmatch(rangeValue)
	err := errors.Errorf("wrong format for rangeValue %s", rangeValue)
	if len(matchAllowed) != 5 {
		return nil, nil, err
	}
	left, leftV, rightV, right := matchAllowed[1], matchAllowed[2], matchAllowed[3], matchAllowed[4]
	return []string{left, right}, []string{leftV, rightV}, nil
}

// ParseFloat32ExprRange 解析范围格式
// 会把值转换成 float32, 返回 (['(', ']', ['0', '10'], err)
func ParseFloat32ExprRange(rangeValue string) ([]string, []float32, error) {
	bound, vals, err := ParseRange(rangeValue)
	if err != nil {
		return nil, nil, err
	}
	leftVal, err1 := strconv.ParseFloat(vals[0], 32)
	rightVal, err2 := strconv.ParseFloat(vals[1], 32)
	if err1 != nil || err2 != nil {
		return nil, nil, err
	} else if leftVal > rightVal {
		return nil, nil, err
	}
	return bound, []float32{float32(leftVal), float32(rightVal)}, nil
}

// CheckInEnums TODO
// 当 valueAllowed 允许为空时，比如 "ON|OFF|"，渲染时表示要把 value 为空渲染出来，类似 --sql-mode=”
// 注意与 CheckInBool 进行区分
func CheckInEnums(valueGiven, valueAllowed string, multiple bool) error {
	// valueGiven := "abc"
	//  valueAllowed := "abc | def" // 会转换成 "abc def"
	valueAlloweds, err := ParseExprEnums(valueAllowed)
	if err != nil {
		return err
	}
	if !multiple { // 单选
		if !util.StringsHas(valueAlloweds, valueGiven) {
			return errors.Errorf("expect one of %s but given %s", valueAlloweds, valueGiven)
		}
	} else { // 多选
		valueGivens := strings.Split(valueGiven, ",")
		for _, g := range valueGivens {
			if !util.StringsHas(valueAlloweds, g) {
				return errors.Errorf("expect multi of %s but given %s", valueAlloweds, g)
			}
		}
		// 多值允许空值时，空值与具体值，不能同时存在
		if len(valueGivens) >= 2 &&
			(util.StringsHas(valueGivens, "''") || util.StringsHas(valueGivens, "\"\"") || util.StringsHas(valueGivens, "")) {
			return errors.Errorf("empty value cannot be given with non-empty value")
		}
	}

	return nil
}

// CheckInRange TODO
func CheckInRange(value, valueAllowed string) error {
	// valueGiven := float32(1)
	// valueAllowed := "(0, 2]"
	tmp, _ := strconv.ParseFloat(value, 32)
	valueGiven := float32(tmp)
	direct, values, err := ParseFloat32ExprRange(valueAllowed)
	if err != nil {
		return err
	}
	err = errors.Errorf("value %s is not in range %s", value, valueAllowed)
	if direct[0] == "[" { // left
		if valueGiven < values[0] {
			return err
		}
	} else {
		if valueGiven <= values[0] {
			return err
		}
	}
	if direct[1] == "]" { // right
		if valueGiven > values[1] {
			return err
		}
	} else {
		if valueGiven >= values[1] {
			return err
		}
	}
	return nil
}

// CheckInSizeRange TODO
func CheckInSizeRange(value, valueAllowed string) error {
	sizeBytes, err := util.ParseSizeInBytesE(value)
	if err != nil {
		return err
	}
	subType := AutoDetectTypeSub(valueAllowed)
	if subType == DTypeSubRange {
		bound, vals, err := ParseRange(valueAllowed)
		if err != nil {
			return nil
		}
		leftVal := util.ParseSizeInBytes(vals[0])
		rightVal := util.ParseSizeInBytes(vals[1])
		valueAllowedNew := fmt.Sprintf("%s%d, %d%s", bound[0], leftVal, rightVal, bound[1])
		valueNew := cast.ToString(sizeBytes)
		return CheckInRange(valueNew, valueAllowedNew)
	} else if subType == DTypeSubEnum {
		return CheckInEnums(value, valueAllowed, false)
	}
	// 如果 valueAllowed='' 或者 位置 subType，默认放通
	return nil
}

// CheckInDuration TODO
// 数字不带单位，默认是 秒s
func CheckInDuration(value, valueAllowed string) error {
	dura, err := util.ToDurationExtE(value)
	if err != nil {
		return err
	}
	subType := AutoDetectTypeSub(valueAllowed)
	if subType == DTypeSubRange {
		bound, vals, err := ParseRange(valueAllowed)
		if err != nil {
			return nil
		}
		leftVal := util.ToDurationExt(vals[0]).Seconds()
		rightVal := util.ToDurationExt(vals[1]).Seconds()
		valueAllowedNew := fmt.Sprintf("%s%d, %d%s", bound[0], int(leftVal), int(rightVal), bound[1])
		valueNew := cast.ToString(int(dura.Seconds()))
		return CheckInRange(valueNew, valueAllowedNew)
	} else if subType == DTypeSubEnum {
		return CheckInEnums(value, valueAllowed, false)
	}
	// 如果 valueAllowed='' 或者 位置 subType，默认放通
	return nil
}

// CheckInRegex TODO
func CheckInRegex(valueGiven, valueAllowed string) error {
	// valueGiven := "1.1.1.1"
	// valueAllowed := "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(#\\d+)?$"
	reg, err := regexp.Compile(valueAllowed)
	if err != nil {
		return errors.Errorf("invalid regex %s", valueAllowed)
	}
	if reg.MatchString(valueGiven) {
		return nil
	} else {
		return errors.Errorf("value %s match regex failed %s", valueGiven, valueAllowed)
	}
}

// CheckInJson TODO
func CheckInJson(valueGiven string) error {
	var js json.RawMessage
	err := json.Unmarshal([]byte(valueGiven), &js)
	// if json.Valid([]byte(valueGiven)) {
	if err != nil {
		return errors.Errorf("invalid json %s", valueGiven)
	} else {
		return nil
	}
}

// CheckGoValidate TODO
func CheckGoValidate(valueGiven, valueAllowed string) error {
	vali := validator.New()
	err := vali.Var(valueGiven, valueAllowed)
	if _, ok := err.(*validator.InvalidValidationError); ok {
		return errors.Wrap(err, "invalid string to validate")
	}
	uni := ut.New(en.New())
	trans, _ := uni.GetTranslator("en")
	if err := en_translations.RegisterDefaultTranslations(vali, trans); err != nil {
		return err
	}
	errStrings := make([]string, 0)
	for _, vErr := range err.(validator.ValidationErrors) {
		errStrings = append(errStrings, vErr.Translate(trans))
	}
	if len(errStrings) > 0 {
		return errors.New(strings.Join(errStrings, " || "))
	}
	return nil
}

// CheckInBool TODO
// 当 valueAllowed 允许为空时，比如 "ON|OFF|"，当 valueGiven = ""，表示渲染的时候可以不用值，直接用 --enable 类似的flag
func CheckInBool(valueGiven, valueAllowed string) error {
	if valueGiven == "" && valueAllowed == "" {
		return nil
	}
	return CheckInEnums(valueGiven, valueAllowed, false)
}

// CheckDataType 检验数据类型
func CheckDataType(name, value string) error {
	err2 := errors.Errorf("expect type %s but given value %s", name, value)
	if name == DTypeInt {
		if _, err := strconv.ParseInt(value, 10, 64); err != nil {
			return errors.Wrap(err2, err.Error())
		}
	} else if name == DTypeFloat {
		if _, err := strconv.ParseFloat(value, 32); err != nil {
			return errors.Wrap(err2, err.Error())
		}
	} else if name == DTypeNumber {
		if _, err := strconv.ParseFloat(value, 64); err != nil {
			return errors.Wrap(err2, err.Error())
		}
	} else if name == DTypeBool {
		if _, err := util.ToBoolExtE(value); err != nil {
			return errors.Wrap(err2, err.Error())
		}
	} else if name == "" {
		// return errors.Errorf("empty value_type for value [%s]", value)
	}
	return nil
}

// CheckDataTypeSub TODO
func CheckDataTypeSub(dataType, subType string) error {
	if subType == "" {
		return nil
	}
	if subs, ok := ValueTypeSubRef[dataType]; ok {
		if !util.StringsHas(subs, subType) {
			return errors.Errorf("value_type %s doesnot has sub type %s, allowed %s",
				dataType, subType, subs)
		}
	} else {
		return errors.Errorf("unknown value_type %s", dataType)
	}
	return nil
}

// AutoDetectTypeSub TODO
func AutoDetectTypeSub(valueAllowed string) string {
	if valueAllowed == "" {
		return ""
	}
	if regexRange.MatchString(valueAllowed) {
		return DTypeSubRange
	}
	reg := regexp.MustCompile(`(\|,)`) // enum 分隔符 ParseExprEnums()
	if reg.MatchString(valueAllowed) {
		return DTypeSubEnum
	}
	return ""
}

// ValidateConfValue godoc
// use ConfValue,ValueType,ValueTypeSub,ValueAllowed as params to check
func ValidateConfValue(confValue, valueType, valueTypeSub, valueAllowed string) error {
	if valueType == "" && valueTypeSub == "" && valueAllowed == "" {
		return nil
	}
	if err := CheckDataType(valueType, confValue); err != nil {
		return err
	} else if err = CheckDataTypeSub(valueType, valueTypeSub); err != nil {
		return err
	}
	var invalidErr = errors.Errorf("invalid value_type_sub %s for %s", valueTypeSub, valueType)
	if valueType == DTypeBool {
		// valueTypeSub = DTypeSubEnum
		switch valueTypeSub {
		case DTypeSubEnum, "":
			return CheckInBool(confValue, valueAllowed)
		case DTypeSubFlag:
			return nil
		default:
			return invalidErr
		}
	} else if util.StringsHas([]string{DTypeInt, DTypeFloat, DTypeNumber}, valueType) {
		if valueTypeSub == "" {
			valueTypeSub = AutoDetectTypeSub(valueAllowed)
			if valueTypeSub == "" {
				return errors.Errorf("cannot detect value_type_sub for %s", valueAllowed)
			}
		}
		switch valueTypeSub {
		case DTypeSubEnum:
			return CheckInEnums(confValue, valueAllowed, false)
		case DTypeSubRange:
			return CheckInRange(confValue, valueAllowed)
		default:
			return invalidErr
		}
	} else { // STRING
		if valueAllowed == "" && !(valueTypeSub == DTypeSubJson || valueTypeSub == DTypeSubMap) {
			// JSON,MAP 合法性 不依赖 valueAllowed
			return nil
		}
		switch valueTypeSub {
		case DTypeSubEnum:
			if err := CheckInEnums(confValue, valueAllowed, false); err != nil {
				return err
			}
		case DTypeSubEnums:
			if err := CheckInEnums(confValue, valueAllowed, true); err != nil {
				return err
			}
		case DTypeSubRegex:
			if err := CheckInRegex(confValue, valueAllowed); err != nil {
				return err
			}
		case DTypeSubBytes:
			if err := CheckInSizeRange(confValue, valueAllowed); err != nil {
				return err
			}
		case DTypeSubDuration:
			if err := CheckInDuration(confValue, valueAllowed); err != nil {
				return err
			}
		case DTypeSubJson, DTypeSubMap:
			if err := CheckInJson(confValue); err != nil {
				return err
			}
		case DTypeSubGovalidate:
			if err := CheckGoValidate(confValue, valueAllowed); err != nil {
				return err
			}
		case DTypeSubList:
			// 忽略 value_allowed，只用户返回格式化
			return nil
		case DTypeSubString, "":
			if valueAllowed != "" {
				// value_allowed !='' and value_type_sub=''，要求 conf_value 只能一个值即 value_allowed
				if confValue != valueAllowed {
					return errors.Errorf("value must equal value_allowed:%s", valueAllowed)
				}
				return nil
			}
			return nil
		default:
			return invalidErr
		}
	}

	return nil
}
