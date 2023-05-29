package util

import (
	"bytes"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/asn1"
	"encoding/base64"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"os"
)

const (
	// RSA_ALGORITHM_SIGN TODO
	RSA_ALGORITHM_SIGN = crypto.SHA256
)

// XRsa TODO
type XRsa struct {
	publicKey  *rsa.PublicKey
	privateKey *rsa.PrivateKey
}

// CreateKeyFile 创建公钥、私钥文件
func CreateKeyFile() error {
	var fpPub, fpPriv *os.File
	var err error

	defer func() {
		fpPub.Close()
		fpPriv.Close()
	}()

	_, errPub := os.Stat("./pubkey.pem")
	_, errPriv := os.Stat("./privkey.pem")
	if os.IsNotExist(errPub) || os.IsNotExist(errPriv) {
		fpPub, err = os.Create("./pubkey.pem")
		if err != nil {
			return fmt.Errorf("公钥文件创建失败 errInfo:%s", err)
		}
		fpPriv, err = os.Create("./privkey.pem")
		if err != nil {
			return fmt.Errorf("私钥文件创建失败 errinfo:%s", err)
		}
		err = CreateKeys(fpPub, fpPriv, 1024)
		if err != nil {
			return fmt.Errorf("密钥文件生成失败 errinfo:%s", err)
		}
	} else if errPub != nil {
		return fmt.Errorf("公钥文件pubkey.pem状态错误:%s", errPub.Error())
	} else if errPriv != nil {
		return fmt.Errorf("私钥文件privkey.pem状态错误:%s", errPub.Error())
	}
	return nil
}

// CreateKeys 生成密钥对
func CreateKeys(publicKeyWriter, privateKeyWriter io.Writer, keyLength int) error {
	// 生成私钥文件
	privateKey, err := rsa.GenerateKey(rand.Reader, keyLength)
	if err != nil {
		return err
	}
	derStream := MarshalPKCS8PrivateKey(privateKey)
	block := &pem.Block{
		Type:  "PRIVATE KEY",
		Bytes: derStream,
	}
	err = pem.Encode(privateKeyWriter, block)
	if err != nil {
		return err
	}
	// 生成公钥文件
	publicKey := &privateKey.PublicKey
	derPkix, err := x509.MarshalPKIXPublicKey(publicKey)
	if err != nil {
		return err
	}
	block = &pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: derPkix,
	}
	err = pem.Encode(publicKeyWriter, block)
	if err != nil {
		return err
	}
	return nil
}

// NewXRsa 构造XRsa
func NewXRsa(publicKey []byte, privateKey []byte) (*XRsa, error) {
	xrsa := XRsa{}
	if publicKey != nil {
		block, _ := pem.Decode(publicKey)
		if block == nil {
			return nil, errors.New("public key error")
		}
		pubInterface, err := x509.ParsePKIXPublicKey(block.Bytes)
		if err != nil {
			return nil, err
		}
		pub := pubInterface.(*rsa.PublicKey)
		xrsa.publicKey = pub
	}
	if privateKey != nil {
		block, _ := pem.Decode(privateKey)
		if block == nil {
			return nil, errors.New("private key error!")
		}
		priv, err := x509.ParsePKCS8PrivateKey(block.Bytes)
		if err != nil {
			return nil, err
		}
		pri, ok := priv.(*rsa.PrivateKey)
		if !ok {
			return nil, errors.New("private key not supported")
		}
		xrsa.privateKey = pri
	}
	return &xrsa, nil
}

// PublicEncrypt 公钥加密
func (r *XRsa) PublicEncrypt(data string) (string, error) {
	partLen := r.publicKey.N.BitLen()/8 - 11
	chunks := split([]byte(data), partLen)
	buffer := bytes.NewBufferString("")
	for _, chunk := range chunks {
		bytes, err := rsa.EncryptPKCS1v15(rand.Reader, r.publicKey, chunk)
		if err != nil {
			return "", err
		}
		buffer.Write(bytes)
	}
	return base64.StdEncoding.EncodeToString(buffer.Bytes()), nil
}

// PrivateDecrypt 私钥解密
func (r *XRsa) PrivateDecrypt(encrypted string) (string, error) {
	// partLen := r.publicKey.N.BitLen() / 8  导致 "panic":"invalid memory address or nil pointer dereference"
	partLen := r.privateKey.N.BitLen() / 8
	// partLen := r.publicKey.N.BitLen() / 8
	// raw, err := base64.StdEncoding.DecodeString(encrypted)
	raw, err := base64.StdEncoding.DecodeString(encrypted)
	chunks := split([]byte(raw), partLen)
	buffer := bytes.NewBufferString("")
	for _, chunk := range chunks {
		decrypted, err := rsa.DecryptPKCS1v15(rand.Reader, r.privateKey, chunk)
		if err != nil {
			return "", err
		}
		buffer.Write(decrypted)
	}
	return buffer.String(), err
}

// Sign 数据加签
func (r *XRsa) Sign(data string) (string, error) {
	h := RSA_ALGORITHM_SIGN.New()
	h.Write([]byte(data))
	hashed := h.Sum(nil)
	sign, err := rsa.SignPKCS1v15(rand.Reader, r.privateKey, RSA_ALGORITHM_SIGN, hashed)
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(sign), err
}

// Verify 数据验签
func (r *XRsa) Verify(data string, sign string) error {
	h := RSA_ALGORITHM_SIGN.New()
	h.Write([]byte(data))
	hashed := h.Sum(nil)
	decodedSign, err := base64.StdEncoding.DecodeString(sign)
	if err != nil {
		return err
	}
	return rsa.VerifyPKCS1v15(r.publicKey, RSA_ALGORITHM_SIGN, hashed, decodedSign)
}

// MarshalPKCS8PrivateKey TODO
func MarshalPKCS8PrivateKey(key *rsa.PrivateKey) []byte {
	info := struct {
		Version             int
		PrivateKeyAlgorithm []asn1.ObjectIdentifier
		PrivateKey          []byte
	}{}
	info.Version = 0
	info.PrivateKeyAlgorithm = make([]asn1.ObjectIdentifier, 1)
	info.PrivateKeyAlgorithm[0] = asn1.ObjectIdentifier{1, 2, 840, 113549, 1, 1, 1}
	info.PrivateKey = x509.MarshalPKCS1PrivateKey(key)
	k, _ := asn1.Marshal(info)
	return k

}

func split(buf []byte, lim int) [][]byte {
	var chunk []byte
	chunks := make([][]byte, 0, len(buf)/lim+1)
	for len(buf) >= lim {
		chunk, buf = buf[:lim], buf[lim:]
		chunks = append(chunks, chunk)
	}
	if len(buf) > 0 {
		chunks = append(chunks, buf[:len(buf)])
	}
	return chunks
}
