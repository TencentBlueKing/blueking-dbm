package iocrypt

import (
	"fmt"
	"os"

	"github.com/minio/sio"
	"golang.org/x/crypto/scrypt"
)

func De() {
	// encryptTool:ncrypt
	// https://pkg.go.dev/github.com/minio/sio
	var err error
	password := "xx"
	salt := "xx"
	key, err := scrypt.Key([]byte(password), []byte(salt), 32768, 8, 1, 32)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to derive encryption key: %v", err)
		fmt.Fprintln(os.Stderr)
		return
	}
	in, err := os.Open("aa.zip")
	out, err := os.Create("bb.zip")
	//_, err = sio.Encrypt(out, in, sio.Config{Key: key})
	//if err != nil {
	// fmt.Fprintf(os.Stderr, "Failed to encrypt data: %v", err)
	// fmt.Fprintln(os.Stderr)
	// return
	//}
	_, err = sio.Decrypt(out, in, sio.Config{Key: key})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to decrypt data: %v", err)
		fmt.Fprintln(os.Stderr)
		return
	}
}
