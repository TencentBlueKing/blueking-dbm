package validatestruct

import "bk-dbconfig/pkg/util"

type MysqlCnfBytes struct {
	value       string
	sizeInBytes int64
}

func MustNewMysqlCnfBytes(value string) MysqlCnfBytes {
	sizeInBytes, err := util.ParseSizeInBytesE(value)
	if err != nil {
		return MysqlCnfBytes{value: value}
	}
	t := MysqlCnfBytes{
		value:       value,
		sizeInBytes: sizeInBytes,
	}
	return t
}

func (m MysqlCnfBytes) Type() string {
	return "BYTES"
}

func (m MysqlCnfBytes) Valid() bool {
	if _, err := util.ParseSizeInBytesE(m.value); err == nil {
		return true
	}
	return false
}

func (m MysqlCnfBytes) String() string {
	return m.value
}

func (m MysqlCnfBytes) Equal(n MysqlCnfBytes) bool {
	return m.sizeInBytes == n.sizeInBytes
}

func (m MysqlCnfBytes) Gt(n MysqlCnfBytes) bool {
	return m.sizeInBytes > n.sizeInBytes
}

func (m MysqlCnfBytes) Lt(n MysqlCnfBytes) bool {
	return m.sizeInBytes < n.sizeInBytes
}

func (m MysqlCnfBytes) Gte(n MysqlCnfBytes) bool {
	return m.sizeInBytes >= n.sizeInBytes
}

func (m MysqlCnfBytes) Lte(n MysqlCnfBytes) bool {
	return m.sizeInBytes <= n.sizeInBytes
}
