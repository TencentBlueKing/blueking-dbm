package common

import (
	"encoding/json"
	"fmt"
	"strings"
)

// GetFcv 对应 GetFCV（js_cmd）--eval 输出的返回。
// featureCompatibilityVersion 通常为嵌套对象 {"version": "M.m"}；部分版本可能为字符串。
type GetFcv struct {
	FeatureCompatibilityVersion fcvFeatureCompatValue `json:"featureCompatibilityVersion"`
	Ok                          bool                  `json:"ok"`
	Errmsg                      string                `json:"errmsg,omitempty"`
}

// ParseGetFcvJSON 解析 mongo --eval 输出的纯 JSON（见 js_cmd 中 JSON.stringify）。
// 不可用 mongo shell 直接 print 命令结果：其中含 Timestamp/BinData 等扩展类型，非合法 JSON。
func ParseGetFcvJSON(s string) (string, error) {
	s = strings.TrimSpace(s)
	if idx := strings.LastIndex(s, "\n"); idx >= 0 {
		// tolerate warnings/noise lines from mongo shell, parse the last output line first
		last := strings.TrimSpace(s[idx+1:])
		if last != "" {
			s = last
		}
	}
	var ver string
	if err := json.Unmarshal([]byte(s), &ver); err == nil {
		if ver == "" {
			return "", fmt.Errorf("empty featureCompatibilityVersion")
		}
		return ver, nil
	}
	var fcv GetFcv
	if err := json.Unmarshal([]byte(s), &fcv); err != nil {
		return "", err
	}
	if fcv.Errmsg != "" {
		return "", fmt.Errorf("featureCompatibilityVersion: %s", fcv.Errmsg)
	}
	if fcv.FeatureCompatibilityVersion.Version == "" {
		return "", fmt.Errorf("empty featureCompatibilityVersion")
	}
	return fcv.FeatureCompatibilityVersion.Version, nil
}

// fcvFeatureCompatValue 兼容 JSON 字符串 "3.6" 与对象 {"version": "3.6"}。
type fcvFeatureCompatValue struct {
	Version string
}

func (v *fcvFeatureCompatValue) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err == nil {
		v.Version = s
		return nil
	}
	var nested struct {
		Version string `json:"version"`
	}
	if err := json.Unmarshal(data, &nested); err != nil {
		return err
	}
	v.Version = nested.Version
	return nil
}

// SetFcv 设置fcv
type SetFcv struct {
	SetFeatureCompatibilityVersion string `json:"setFeatureCompatibilityVersion"`
	Confirm                        bool   `json:"confirm,omitempty"`
}
