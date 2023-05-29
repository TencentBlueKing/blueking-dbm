package api

import "encoding/json"

// X-Bkapi-Authorization:[{"bk_app_code": "bk_dbm", "bk_app_secret": "72fec2b4-512b-4c4d-b5d2-572f634af641", "bk_username": "admin"}]
// X-Request-Id:[96d76806-dcf6-11ed-b47f-020b20fcf451]]

// BKAuthorization TODO
type BKAuthorization struct {
	BKAppCode   string `json:"bk_app_code"`
	BKAppSecret string `json:"bk_app_secret"`
	BKUsername  string `json:"bk_username"`
}

// GetHeaderUsername TODO
func GetHeaderUsername(header string) string {
	if header == "" {
		return ""
	}
	var bkAuth = BKAuthorization{}
	username := ""
	if err := json.Unmarshal([]byte(header), &bkAuth); err != nil {
		return ""
	} else {
		if bkAuth.BKUsername != "" {
			username = bkAuth.BKUsername
		}
	}
	return username
}
