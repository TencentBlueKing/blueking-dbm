package validate

import (
	"github.com/go-playground/validator/v10"
	"github.com/robfig/cron/v3"
)

// validateCrontabExpr 验证Liunx crontab表达式
func validateCrontabExpr(f validator.FieldLevel) bool {
	v := f.Field().String()
	err := validateCronExpr(v)
	return err == nil
}

// validateCronExpr TODO
/**
 * @description: crontab 表达式检查,如果返回error != nil，则表示crontab 表达式不正确
 * @receiver {string} cronstr eg:" * * * 3 5"
 * @return {*}
 */
func validateCronExpr(cronstr string) (err error) {
	specParser := cron.NewParser(cron.Minute | cron.Hour | cron.Dom | cron.Month | cron.Dow)
	_, err = specParser.Parse(cronstr)
	return
}
