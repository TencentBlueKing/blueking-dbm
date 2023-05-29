package safego

import (
	"fmt"
	"runtime/debug"

	"go.uber.org/zap"
)

// Go TODO
func Go(f func()) {
	go func() {
		defer func() {
			if r := recover(); r != nil {
				zap.L().Error(fmt.Sprintf("Panic recovered: %s, stack: %s", r, string(debug.Stack())))
			}
		}()

		f()
	}()
}

// GoArgs 较少用。用此函数启动带任意参数的goroutine，参数类型只能是interface{}，在函数内部再进行类型转换。
func GoArgs(f func(...interface{}), args ...interface{}) {
	go func() {
		defer func() {
			if r := recover(); r != nil {
				zap.L().Error(fmt.Sprintf("Panic recovered: %s, stack: %s", r, string(debug.Stack())))
			}
		}()

		f(args...)
	}()
}
