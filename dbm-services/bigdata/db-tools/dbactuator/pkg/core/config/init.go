// Package config TODO
/*
 * @Date: 2022-04-21 14:50:43
 * @LastEditTime: 2022-04-21 14:50:43
 * @Description:
 * @FilePath: /bk-dbactuator/pkg/core/config/init.go
 */
package config

import (
	"fmt"
	"os"
	"reflect"
	"sync"
)

var (
	_CONFIGS sync.Map
)

// 注册需要解析为struct的配置项。
// * key: 配置项路径。
// * ptrStruct: 配置struct的引用。

// Register TODO
func Register(key string, ptrStruct interface{}) {
	if reflect.TypeOf(ptrStruct).Kind() != reflect.Ptr {
		fmt.Fprintf(os.Stderr, "config.Register need pointer of struct.\n")
		os.Exit(1)
	}

	_CONFIGS.Store(key, ptrStruct)
}
