package util

import "os"

// GetEnvAsInt 从环境变量读取整数值
func GetEnvAsInt(key string, defaultValue int) int {
	if value, exists := os.LookupEnv(key); exists {
		if intValue, err := ParseInt(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

// GetEnvAsBool 从环境变量读取布尔值
func GetEnvAsBool(key string, defaultValue bool) bool {
	if value, exists := os.LookupEnv(key); exists {
		if boolValue, err := ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}

// GetEnv 从环境变量读取字符串
func GetEnv(key string, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
