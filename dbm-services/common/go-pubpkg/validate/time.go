package validate

import (
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// validateTimeStr TODO
// 验证时间字符串 "09:00:00" 这种
func validateTimeStr(f validator.FieldLevel) bool {
	v := f.Field().String()
	if strings.TrimSpace(v) == "" {
		return true
	}
	_, err := time.Parse("15:04:05", v)
	return err == nil
}
