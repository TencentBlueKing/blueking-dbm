package util

import (
	"dbm-services/redis/db-tools/dbactuator/mylog"

	"github.com/go-playground/validator/v10"
)

// ValidateStruct 校验参数有效性
func ValidateStruct(params interface{}) error {
	// 创建一个新的验证器实例
	validate := validator.New()
	// 使用验证器对参数进行校验
	err := validate.Struct(params)
	if err != nil {
		// 如果校验错误是 InvalidValidationError 类型，记录错误并返回
		if _, ok := err.(*validator.InvalidValidationError); ok {
			mylog.Logger.Error(" params validate failed,err:%v,params:%+v",
				err, params)
			return err
		}
		// 如果校验错误是 ValidationErrors 类型，遍历每个错误并记录后返回
		for _, err := range err.(validator.ValidationErrors) {
			mylog.Logger.Error("params validate failed,err:%v,params:%+v",
				err, params)
			return err
		}
	}
	mylog.Logger.Info("params validate success")
	return nil

}
