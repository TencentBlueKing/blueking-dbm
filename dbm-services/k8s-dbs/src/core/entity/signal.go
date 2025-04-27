package entity

import (
	"fmt"
	"math/rand"
	"strconv"
	"strings"
	"time"

	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
)

const letterBytes = "abcdefghijklmnopqrstuvwxyz0123456789"

// AppendRandomSuffix Append Random Suffix
func AppendRandomSuffix(originalStr string, length int) string {
	rand.Seed(time.Now().UnixNano())
	b := make([]byte, length)
	for i := range b {
		b[i] = letterBytes[rand.Intn(len(letterBytes))]
	}
	randomSuffix := string(b)
	return originalStr + randomSuffix
}

// IntToInt32Ptr  transform Int To Int32
func IntToInt32Ptr(num int) *int32 {
	result := int32(num)
	return &result
}

// IntToInt64Ptr  transform Int To Int364
func IntToInt64Ptr(num int) *int64 {
	result := int64(num)
	return &result
}

func ExtractPort(s string) (int32, error) {
	parts := strings.Split(s, ":")
	if len(parts) != 2 {
		return 0, fmt.Errorf("invalid format, expected IP:port")
	}
	portStr := parts[1]
	port, err := strconv.ParseInt(portStr, 10, 32)
	if err != nil {
		return 0, fmt.Errorf("invalid port format: %v", err)
	}
	return int32(port), nil
}

// Int32ToString transform int32 to string
func Int32ToString(num int32) string {
	num64 := int64(num)
	return strconv.FormatInt(num64, 10)
}

// GetBestEffortParallelStrategy Get BestEffortParallel Strategy from kb
func GetBestEffortParallelStrategy() *kbv1.UpdateStrategy {
	s := kbv1.BestEffortParallelStrategy
	return &s
}

// GetRequiredVarOption Get Required Var Option from kb
func GetRequiredVarOption() *kbv1.VarOption {
	vop := kbv1.VarRequired
	return &vop
}

// GetTrue get True Ptr
func GetTrue() *bool {
	temp := true
	return &temp
}

// GetFalse get False Ptr
func GetFalse() *bool {
	temp := false
	return &temp
}

// StringToPointer String To Pointer
func StringToPointer(s string) *string {
	return &s
}

// Int64ToInt32 Int64 To Int32
func Int64ToInt32(num int64) (int32, error) {
	const (
		minInt32 int64 = -2147483648
		maxInt32 int64 = 2147483647
	)
	if num < minInt32 || num > maxInt32 {
		return 0, fmt.Errorf("value out of range for int32")
	}
	return int32(num), nil
}

// GetDefaultServiceName Get DefaultService Name
func GetDefaultServiceName(fullString string) (string, error) {
	if fullString == "" {
		return "", nil
	}
	// 首先按 - 拆分
	parts := strings.Split(fullString, "-")
	if len(parts) >= 2 {
		// 再按. 拆分
		subParts := strings.Split(parts[1], ".")
		if len(subParts) >= 1 {
			return subParts[0], nil
		}
	}
	return "", fmt.Errorf("invalid string format")
}
