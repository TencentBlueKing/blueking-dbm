/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package osutil TODO
package osutil

import (
	"bytes"
	"fmt"
	"io"
	"math/rand"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
)

// StringToMap 字符串 TO map
// 如db1,,db2,db3,db2 ,等去重并转换成db1,db2,db3
func StringToMap(srcStr string, seq string) map[string]struct{} {
	splitReg := regexp.MustCompile(seq)
	strList := splitReg.Split(srcStr, -1)
	strMap := make(map[string]struct{})
	for _, str := range strList {
		if len(strings.TrimSpace(str)) == 0 {
			continue
		}
		strMap[strings.TrimSpace(str)] = struct{}{}
	}
	return strMap
}

// FileExist TODO
func FileExist(fileName string) bool {
	_, err := os.Stat(fileName)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}

// SplitName 切分用户传过来的IP字符串列表等
// 切分规则：
// 把\r+|\s+|;+|\n+|,+这些分隔符，转成字符串数组
// 返回字符串数组
func SplitName(input string) ([]string, error) {
	if reg, err := regexp.Compile(`\r+|\s+|;+|\n+`); err != nil {
		return nil, err
	} else {
		input = reg.ReplaceAllString(input, ",")
	}
	if reg, err := regexp.Compile(`^,+|,+$`); err != nil {
		return nil, err
	} else {
		input = reg.ReplaceAllString(input, "")
	}
	if reg, err := regexp.Compile(`,+`); err != nil {
		return nil, err
	} else {
		input = reg.ReplaceAllString(input, ",")
	}
	result := strings.Split(input, ",")
	return result, nil
}

// Uniq 对字符串数组进行去重
func Uniq(input []string) []string {
	var newData []string
	if len(input) > 0 {
		temp := map[string]bool{}
		for _, value := range input {
			temp[value] = true
		}
		for k := range temp {
			newData = append(newData, k)
		}
	}
	return newData
}

// WrapFileLink TODO
func WrapFileLink(link string) string {
	name := filepath.Base(link)
	return fmt.Sprintf(`<a target="_blank" href="%s" class="link-item">%s</a>`, link, name)
}

// CapturingPassThroughWriter is a writer that remembers
// data written to it and passes it to w
type CapturingPassThroughWriter struct {
	buf bytes.Buffer
	w   io.Writer
}

// NewCapturingPassThroughWriter creates new CapturingPassThroughWriter
func NewCapturingPassThroughWriter(w io.Writer) *CapturingPassThroughWriter {
	return &CapturingPassThroughWriter{
		w: w,
	}
}

// Write 用于常见IO
func (w *CapturingPassThroughWriter) Write(d []byte) (int, error) {
	w.buf.Write(d)
	return w.w.Write(d)
}

// Bytes returns bytes written to the writer
func (w *CapturingPassThroughWriter) Bytes() []byte {
	return w.buf.Bytes()
}

// ReadFileString TODO
func ReadFileString(filename string) (string, error) {
	if body, err := os.ReadFile(filename); err != nil {
		return "", err
	} else {
		return string(body), nil
	}
}

// GetInstallName 根据端口号拼接sqlserver的实例名称，比如48322，那么端口号是S48322
func GetInstallName(port int) string {
	return fmt.Sprintf("S%d", port)
}

// GetVersionYears 根据版本号信息提取版本年份
func GetVersionYears(SQlServerVersion string) (int, error) {
	re := regexp.MustCompile(`\d+`)
	match := re.FindString(SQlServerVersion)
	num, err := strconv.Atoi(match)
	if err != nil {
		return 0, fmt.Errorf("error converting string to int:[%v] ", err)
	}
	return num, nil
}

// GetInstallPackageName 根据压缩包，得到
func GetInstallPackageName(name string) string {
	return strings.Split(name, ".")[0]
}

// GenerateRandomString 随机生成字符串
func GenerateRandomString(length int) string {
	seed := time.Now().UnixNano()
	rng := rand.New(rand.NewSource(seed))

	// 定义包含所有可能字符的字符集
	charset := cst.LETTERS

	// 生成随机字符串
	result := make([]byte, length)
	for i := 0; i < length; i++ {
		result[i] = charset[rng.Intn(len(charset))]
	}

	return string(result)
}

// GetListenPort 根据实例端口计算出endpoint 监听端口
func GetListenPort(port int) int {
	temp := port % 100
	newTemp := (temp%10)*10 + (temp / 10)
	listenPort := (port - 11300) - temp + newTemp

	if listenPort <= 0 {
		listenPort = 37022
	}
	return listenPort
}

// ArrayTransString 根据传入的数组，转成对应字符串
// 转换格式：[a,b,c] 转换成："'a','b','c'"
func ArrayTransString(arr []string) string {
	// 使用循环和字符串拼接
	var str string
	for _, item := range arr {
		str += fmt.Sprintf("'%s',", item)
	}
	str = strings.TrimRight(str, ",")
	return str
}

// CreateExporterConf 简单写一个根据端口号生成exporter文件的方法
func CreateExporterConf(fileName string, host string, port int, user string, password string) (err error) {
	// 检查文件是否存在
	if _, err := os.Stat(fileName); err == nil {
		// 文件存在，删除文件
		err := os.Remove(fileName)
		if err != nil {
			return err
		}
	}
	// 创建文件
	file, err := os.Create(fileName)
	if err != nil {
		return err
	}
	defer file.Close()
	file.WriteString(fmt.Sprintf("%s %d %s %s false false", host, port, user, password))
	return nil
}
