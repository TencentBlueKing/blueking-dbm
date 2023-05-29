package util

import (
	"fmt"
	"strings"
)

type arg struct {
	v     string
	isPwd bool
}

// CmdBuilder 用于生成给sh执行的命令行
// 支持标记密码参数，用于生成不带密码的命令行

// CmdBuilder TODO
type CmdBuilder struct {
	Args []arg
}

// NewCmdBuilder TODO
func NewCmdBuilder() *CmdBuilder {
	c := CmdBuilder{}
	return &c
}

// Append TODO
func (c *CmdBuilder) Append(v ...string) *CmdBuilder {
	for _, vv := range v {
		c.Args = append(c.Args, arg{vv, false})
	}
	return c
}

// AppendPassword TODO
func (c *CmdBuilder) AppendPassword(v string) *CmdBuilder {
	c.Args = append(c.Args, arg{v, true})
	return c
}

// GetCmd TODO
func (c *CmdBuilder) GetCmd() []string {
	tmpSlice := make([]string, 0, len(c.Args))
	for i := range c.Args {
		tmpSlice = append(tmpSlice, c.Args[i].v)
	}

	return tmpSlice
}

// GetCmdLine TODO
func (c *CmdBuilder) GetCmdLine(suUser string, replacePassword bool) string {
	tmpSlice := make([]string, 0, len(c.Args))
	for i := range c.Args {
		if replacePassword && c.Args[i].isPwd {
			tmpSlice = append(tmpSlice, "xxx")
		} else {
			tmpSlice = append(tmpSlice, c.Args[i].v)
		}
	}
	cmdLine := strings.Join(tmpSlice, " ")
	if suUser != "" {
		return fmt.Sprintf(`su %s -c "%s"`, suUser, cmdLine)
	}
	return cmdLine
}
