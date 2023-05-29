package httpclient

import (
	"time"

	"github.com/golang-jwt/jwt"
)

const (
	secretId  string = "2d96cd392adb4d29bcd52fa48d5b4352"
	secretKey string = "Xu1I~TDqB0dUR9Zj"
)

// Sign TODO
func Sign(rtx string) (tokenString string, err error) {
	// The token content.
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":  secretId,
		"user": rtx,
		"iat":  time.Now().Add(-1 * time.Minute).Unix(),
	})
	// Sign the token with the specified secret.
	tokenString, err = token.SignedString([]byte(secretKey))
	return
}
