package cmutil

import (
	"strings"
	"unicode"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"github.com/spf13/viper"
)

// ViperGetSizeInBytes TODO
func ViperGetSizeInBytes(key string) int64 {
	return ParseSizeInBytes(viper.GetString(key))
}

// ViperGetSizeInBytesE TODO
func ViperGetSizeInBytesE(key string) (int64, error) {
	return ParseSizeInBytesE(viper.GetString(key))
}

// ParseSizeInBytesE converts strings like 1GB or 12 mb into an unsigned integer number of bytes
// if sizeStr has no suffix b/B, append to it
// b will be treated as B, can not handle 1GiB like
func ParseSizeInBytesE(sizeStr string) (size int64, err error) {
	sizeStr = strings.TrimSpace(strings.ToLower(sizeStr))
	if unicode.ToLower(rune(sizeStr[len(sizeStr)-1])) != 'b' {
		sizeStr += "b"
	}
	lastChar := len(sizeStr) - 1
	multiplier := uint(1)
	if lastChar > 0 {
		if sizeStr[lastChar] == 'b' || sizeStr[lastChar] == 'B' {
			if lastChar > 1 {
				switch unicode.ToLower(rune(sizeStr[lastChar-1])) {
				case 'k':
					multiplier = 1 << 10
					sizeStr = strings.TrimSpace(sizeStr[:lastChar-1])
				case 'm':
					multiplier = 1 << 20
					sizeStr = strings.TrimSpace(sizeStr[:lastChar-1])
				case 'g':
					multiplier = 1 << 30
					sizeStr = strings.TrimSpace(sizeStr[:lastChar-1])
				default:
					multiplier = 1
					sizeStr = strings.TrimSpace(strings.TrimSuffix(sizeStr, "b"))
				}
			} else if lastChar == 1 {
				multiplier = 1
				sizeStr = strings.TrimSpace(strings.TrimSuffix(sizeStr, "b"))
			}
		}
	}
	if strings.Contains(sizeStr, ".") {
		sizeFloat, err := cast.ToFloat64E(sizeStr)
		if err != nil {
			return -1, errors.Errorf("parse failed to bytes: %s", sizeStr)
		}
		size = safeMulFloat(sizeFloat, int64(multiplier))
	} else {
		size, err = cast.ToInt64E(sizeStr)
		if err != nil {
			return -1, errors.Errorf("parse failed to bytes: %s", sizeStr)
		}
		size = safeMul(size, int64(multiplier))
	}
	if size < 0 {
		return -2, errors.Errorf("bytes canot be negative: %s", sizeStr)
	}
	return size, nil
}

func safeMul(a, b int64) int64 {
	c := a * b
	if a > 1 && b > 1 && c/b != a {
		return 0
	}
	return c
}

// safeMulFloat WARN: bytes will lose precision
func safeMulFloat(a float64, b int64) int64 {
	c := a * float64(b)
	return int64(c)
}

// ParseSizeInBytes 将 gb, MB 转换成 bytes 数字. b 不区分大小写，代表 1字节
// ignore error
func ParseSizeInBytes(sizeStr string) int64 {
	sizeBytes, err := ParseSizeInBytesE(sizeStr)
	if err != nil {
		sizeBytes = 0
	} else if sizeBytes < 0 {
		sizeBytes = 0
	}
	return sizeBytes
}
