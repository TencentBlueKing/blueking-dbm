package iocrypt

import (
	"fmt"
	"io"
	"os"
)

// doEncryptFile example
// usually use cmutil EncryptOpt
func doEncryptFile() error {
	srcFilename := "aaa.tar"
	srcFile, err := os.Open(srcFilename)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	encryptTool := Openssl{CryptCmd: "openssl", EncryptElgo: AlgoAES256CBC, EncryptKey: "aaa"}
	encryptFile, err := os.OpenFile(srcFilename+"."+encryptTool.DefaultSuffix(),
		os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0644)
	if err != nil {
		return err
	}
	defer encryptFile.Close()

	xbw, err := FileEncryptWriter(&encryptTool, encryptFile)
	if err != nil {
		return err
	}
	written, err := io.Copy(xbw, srcFile)
	err1 := xbw.Close()
	if err != nil {
		fmt.Println("write eeeee")
		return err
	}
	if err1 != nil {
		return err1
	}
	fmt.Println("written bytes", written)
	return nil
}
