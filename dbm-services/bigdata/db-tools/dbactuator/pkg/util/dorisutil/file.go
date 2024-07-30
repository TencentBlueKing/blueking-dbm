package dorisutil

import (
	"bytes"
	"fmt"
)

// TransMapToFileBytes 将map使用拼接字符串 拼接为文件
func TransMapToFileBytes(source map[string]string, concatWord string, separateWord string) ([]byte, error) {
	buff := bytes.Buffer{}

	for k, v := range source {
		// ignore WriteString method return err, need to improve
		buff.WriteString(k)
		buff.WriteString(concatWord)
		buff.WriteString(v)
		buff.WriteString(separateWord)
	}

	return buff.Bytes(), nil
}

// DefaultTransMap2Bytes 默认用于key=value的配置文件生成
func DefaultTransMap2Bytes(source map[string]string) ([]byte, error) {
	return TransMapToFileBytes(source, "=", fmt.Sprintln())
}
