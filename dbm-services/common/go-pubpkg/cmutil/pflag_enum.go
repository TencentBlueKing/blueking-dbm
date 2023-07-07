package cmutil

import (
	"errors"
	"fmt"

	"github.com/spf13/pflag"
)

/* 使用示例
formatOpt, err := cmutil.NewPflagEnum("format", "table", []string{"table", "json"})
// judge err
spiderQueryCmd.Flags().Var(formatOpt, formatOpt.Name(),fmt.Sprintf("output format, allowed %v", formatOpt.Choices()))
err = formatOpt.SetChoices(spiderQueryCmd.Flags())
// judge err
_ = viper.BindPFlag("query.format", spiderQueryCmd.Flags().Lookup("format"))
*/

// PflagEnum 自定义的 pflag 类型，选项必须从事允许的值列表里面选择
type PflagEnum struct {
	// name flag 选项名称
	name string
	// valueDefault 默认值
	valueDefault string
	// choices 可选项
	choices []string

	value string
	flag  *pflag.Flag
}

func NewPflagEnum(name string, value string, choices []string) (*PflagEnum, error) {
	// validate valueDefault is in choices
	isValueDefaultOk := false
	for _, c := range choices {
		if c == value {
			isValueDefaultOk = true
			break
		}
	}
	if !isValueDefaultOk {
		return nil, fmt.Errorf("default value %s is not one of %v", value, choices)
	}
	return &PflagEnum{
		name:         name,
		valueDefault: value,
		choices:      choices,
	}, nil
}

// SetChoices 要先通过 yourCmd.Flags().Var 注册 name，才能调用 SetChoices
func (e *PflagEnum) SetChoices(flagSet *pflag.FlagSet) error {
	if e.name == "" {
		return errors.New("flag name cannot be empty, please register it using yourCmd.Flags().Var")
	}
	e.flag = flagSet.Lookup(e.name)
	if e.flag == nil {
		return errors.New("unknown choices error, may lookup name error")
	}
	return flagSet.SetAnnotation(e.name, "choices", e.choices)
}

// String is used both by fmt.Print and by Cobra in help text
func (e *PflagEnum) String() string {
	return e.value
}

// Set must have pointer receiver so it doesn't change the value of a copy
func (e *PflagEnum) Set(v string) error {

	choices, ok := e.flag.Annotations["choices"]
	if !ok {
		return errors.New("no choices given")
	}
	for _, c := range choices {
		if c == v {
			e.value = v
			return nil
		}
	}
	return fmt.Errorf(`must be one of %v`, choices)
}

// Type is only used in help text
func (e *PflagEnum) Type() string {
	return "PflagEnum"
}

// Name return name
func (e *PflagEnum) Name() string {
	return e.name
}

// Choices return choices
func (e *PflagEnum) Choices() []string {
	return e.choices
}
