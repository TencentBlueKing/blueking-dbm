package cmutil

import (
	"errors"
	"fmt"
	"strings"

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

// PflagEnums 自定义的 pflag 类型，选项必须从事允许的值列表里面选择
type PflagEnums struct {
	// name flag 选项名称
	name string
	// valueDefault 默认值
	valueDefault string
	// choices 可选项
	choices []string

	value string
	flag  *pflag.Flag
}

func NewPflagEnums(name string, value string, choices []string) (*PflagEnums, error) {
	// validate valueDefault is in choices
	values := strings.Split(value, ",")
	for _, val := range values {
		isInChoose := false
		for _, c := range choices {
			if c == val {
				isInChoose = true
				break
			}
		}
		if !isInChoose {
			return nil, fmt.Errorf(`default value all %s must be one of %v`, value, choices)
		}
	}

	return &PflagEnums{
		name:         name,
		valueDefault: value,
		choices:      choices,
	}, nil
}

// SetChoices 要先通过 yourCmd.Flags().Var 注册 name，才能调用 SetChoices
func (e *PflagEnums) SetChoices(flagSet *pflag.FlagSet) error {
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
func (e *PflagEnums) String() string {
	return e.value
}

// Set must have pointer receiver so it doesn't change the value of a copy
func (e *PflagEnums) Set(v string) error {
	choices, ok := e.flag.Annotations["choices"]
	if !ok {
		return errors.New("no choices given")
	}
	values := strings.Split(v, ",")
	for _, val := range values {
		isInChoose := false
		for _, c := range choices {
			if c == val {
				isInChoose = true
				break
			}
		}
		if !isInChoose {
			return fmt.Errorf(`%s is not one of %v`, val, choices)
		}
	}
	e.value = v
	return nil
}

// Type is only used in help text
func (e *PflagEnums) Type() string {
	return "PflagEnum"
}

// Name return name
func (e *PflagEnums) Name() string {
	return e.name
}

// Choices return choices
func (e *PflagEnums) Choices() []string {
	return e.choices
}
