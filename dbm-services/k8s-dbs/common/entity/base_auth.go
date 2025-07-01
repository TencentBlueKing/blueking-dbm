package entity

// BKAuth 封装认证授权
type BKAuth struct {
	BkAppCode   string `json:"bk_app_code,omitempty"`
	BkAppSecret string `json:"bk_app_secret,omitempty"`
	BkUserName  string `json:"bk_username,omitempty"`
}
