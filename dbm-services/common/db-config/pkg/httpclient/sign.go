package httpclient

import (
	"time"

	"github.com/golang-jwt/jwt/v4"
)

const (
	secretId  string = "test"
	secretKey string = "test"
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
