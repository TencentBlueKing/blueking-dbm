// Package serialize TODO
package serialize

import (
	"bk-dbconfig/pkg/util/compress"
	"encoding/base64"

	"github.com/pkg/errors"
	"github.com/vmihailenco/msgpack/v5"
)

// SerializeToString TODO
// serialize, compress, base64.Encode
func SerializeToString(v interface{}, compression bool) (string, error) {
	b, err := msgpack.Marshal(v)
	if err != nil {
		return "", err
	}
	if compression {
		if b, err = compress.GzipBytes(b); err != nil {
			return "", err
		}
	}
	s := base64.StdEncoding.EncodeToString(b)
	return s, nil
}

// UnSerializeString TODO
// base64.Decode, unCompress, unSerialize,
func UnSerializeString(s string, v interface{}, unCompress bool) error {
	if s == "" {
		return errors.New("数据包为空")
	}
	b, err := base64.StdEncoding.DecodeString(s)
	if unCompress {
		if b, err = compress.GunzipBytes(b); err != nil {
			return errors.Wrap(err, "数据包解压失败")
		}
	}
	err = msgpack.Unmarshal(b, &v)
	if err != nil {
		return errors.Wrap(err, "解包失败")
	}
	return nil
}
