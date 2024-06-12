package common

// GetFcv 获取fcv信息
type GetFcv struct {
	FeatureCompatibilityVersion string `json:"featureCompatibilityVersion"`
	Ok                          bool   `json:"ok"`
}

// SetFcv 设置fcv
type SetFcv struct {
	SetFeatureCompatibilityVersion string `json:"setFeatureCompatibilityVersion"`
	Confirm                        bool   `json:"confirm,omitempty"`
}
