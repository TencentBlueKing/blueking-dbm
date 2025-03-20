package validate

import (
	"strings"

	"github.com/go-playground/validator/v10"

	"dbm-services/common/go-pubpkg/cmutil"
)

// TagEnum TODO
const TagEnum = "enums"

// ValidateEnums TODO
// make validate tag work with enums tag
// 避免 validate oneof 和 swagger enums 写 2 份重复的校验和文档
// example: Method string `validate:"required,enums" enums:"post,get" json:"method"`
func ValidateEnums(f validator.FieldLevel) bool {
	fieldValue := f.Field().String()
	fieldName := f.StructFieldName()
	// get StructField
	sf, _ := f.Parent().Type().FieldByName(fieldName)
	// get tag value from tag_field enums
	tagValue := sf.Tag.Get(TagEnum)
	enumsValues := strings.Split(tagValue, ",")
	if cmutil.StringsHas(enumsValues, fieldValue) {
		return true
	} else {
		return false
	}
}

func validCharSet(f validator.FieldLevel) bool {
	v := f.Field().String()
	return cmutil.HasElem(
		v, []string{"default", "utf8mb4", "utf8", "latin1", "gb2312", "gbk", "binary", "gb18030", "utf8mb3"},
	)
}
