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
// withB indicate where sizeStr has suffix b/B
func ParseSizeInBytesE(sizeStr string) (int64, error) {
	sizeStr = strings.TrimSpace(sizeStr)
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
	size, err := cast.ToInt64E(sizeStr)
	if err != nil {
		return -1, errors.Errorf("parse failed to bytes: %s", sizeStr)
	} else if size < 0 {
		return -2, errors.Errorf("bytes canot be negative: %s", sizeStr)
	}
	return safeMul(size, int64(multiplier)), nil
}

func safeMul(a, b int64) int64 {
	c := a * b
	if a > 1 && b > 1 && c/b != a {
		return 0
	}
	return c
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
