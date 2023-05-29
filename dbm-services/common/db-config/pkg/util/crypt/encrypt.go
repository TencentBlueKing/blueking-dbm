// Package crypt TODO
package crypt

import (
	"bk-dbconfig/pkg/util/compress"
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"strings"

	"github.com/pkg/errors"
)

// 加密过程：
//  1、处理数据，对数据进行填充，采用PKCS7（当密钥长度不够时，缺几位补几个几）的方式。
//  2、对数据进行加密，采用AES加密方法中CBC加密模式
//  3、对得到的加密数据，进行base64加密，得到字符串
// 解密过程相反

// 16,24,32位字符串的话，分别对应AES-128，AES-192，AES-256 加密方法
// key不能泄露

const flagEncrypt = "**"

// pkcs7Padding 填充
func pkcs7Padding(data []byte, blockSize int) []byte {
	// 判断缺少几位长度。最少1，最多 blockSize
	padding := blockSize - len(data)%blockSize
	// 补足位数。把切片[]byte{byte(padding)}复制padding个
	padText := bytes.Repeat([]byte{byte(padding)}, padding)
	return append(data, padText...)
}

// pkcs7UnPadding 填充的反向操作
func pkcs7UnPadding(data []byte) ([]byte, error) {
	length := len(data)
	if length == 0 {
		return nil, errors.New("解密字符串错误！")
	}
	// 获取填充的个数
	unPadding := int(data[length-1])
	if num := length - unPadding; num <= 0 {
		return nil, errors.New("解密出现异常")
	} else {
		return data[:num], nil
	}
}

// aesEncrypt 加密
func aesEncrypt(plaintext []byte, key []byte) ([]byte, error) {
	// 创建加密实例
	if len(key) < 32 {
		key = pkcs7Padding(key, 32)
	} else if len(key) > 32 {
		key = key[0:32]
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	// 判断加密快的大小
	blockSize := block.BlockSize()
	// 填充
	plaintext = pkcs7Padding(plaintext, blockSize)
	// 初始化加密数据接收切片
	crypted := make([]byte, len(plaintext))
	// 使用cbc加密模式
	blockMode := cipher.NewCBCEncrypter(block, key[:blockSize])
	// 执行加密
	blockMode.CryptBlocks(crypted, plaintext)
	return crypted, nil
}

// aesDecrypt 解密
func aesDecrypt(ciphertext []byte, key []byte) ([]byte, error) {
	// 创建实例
	if len(key) < 32 {
		key = pkcs7Padding(key, 32)
	} else if len(key) > 32 {
		key = key[0:32]
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	// 获取块的大小
	blockSize := block.BlockSize()
	// 使用cbc
	blockMode := cipher.NewCBCDecrypter(block, key[:blockSize])
	// 初始化解密数据接收切片
	decrypted := make([]byte, len(ciphertext))
	// 执行解密
	blockMode.CryptBlocks(decrypted, ciphertext)
	// 去除填充

	decrypted, err = pkcs7UnPadding(decrypted)
	if err != nil {
		return nil, err
	}
	return decrypted, nil
}

// EncryptByAes Aes加密后，再 base64，最后前面加 ** 表示已加密
func EncryptByAes(data []byte, key []byte, zip bool) (string, error) {
	res, err := aesEncrypt(data, key)
	if err != nil {
		return "", errors.Wrapf(err, "p=%s k=%s, zip=%t", data, key, zip)
	}
	if zip {
		res, err = compress.GzipBytes(res)
		if err != nil {
			return "", errors.Wrapf(err, "p=%s k=%s, zip=%t", data, key, zip)
		}
	}
	base64Str := base64.StdEncoding.EncodeToString(res)
	return flagEncrypt + base64Str, nil
}

// DecryptByAes Aes 解密
func DecryptByAes(data string, key []byte, unzip bool) ([]byte, error) {
	dataByte, err := base64.StdEncoding.DecodeString(data)
	if err != nil {
		return nil, errors.Wrapf(err, "c=%s k=%s, unzip=%t", data, key, unzip)
	}
	if unzip {
		dataByte, err = compress.GunzipBytes(dataByte)
		if err != nil {
			return nil, errors.Wrapf(err, "c=%s k=%s, unzip=%t", data, key, unzip)
		}
	}
	return aesDecrypt(dataByte, key)
}

// IsEncryptedString TODO
func IsEncryptedString(data string) (string, bool) {
	if strings.HasPrefix(data, flagEncrypt) {
		return strings.TrimLeft(data, flagEncrypt), true
	} else {
		return data, false
	}
}

// EncryptString TODO
func EncryptString(p, k string, zip bool) (string, error) {
	if _, isEncrypted := IsEncryptedString(p); isEncrypted {
		return p, nil
	} else if p == "" {
		return "", nil
	}
	return EncryptByAes([]byte(p), []byte(k), zip)
}

// DecryptString TODO
// 如果字符串不是以 ** 开头，表示已是明文，直接返回
func DecryptString(c, k string, unzip bool) (string, error) {
	c, isEncrypted := IsEncryptedString(c) // will trim ** if isEncrypted is true
	if !isEncrypted {
		return c, nil
	}
	// else remove ** prefix from data
	p, e := DecryptByAes(c, []byte(k), unzip)
	return string(p), e
}
