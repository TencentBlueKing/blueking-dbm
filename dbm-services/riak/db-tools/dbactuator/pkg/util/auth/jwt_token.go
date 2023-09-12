package auth

import (
	"time"

	"github.com/golang-jwt/jwt/v4"
	// "github.com/dgrijalva/jwt-go"
)

// Sign 签名加密
func Sign(username string, secretId, secretKey string) (tokenString string, err error) {
	// The token content.
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":  secretId,
		"user": username,
		"iat":  time.Now().Add(-1 * time.Minute).Unix(),
	})
	// Sign the token with the specified secret.
	tokenString, err = token.SignedString([]byte(secretKey))
	return
}
