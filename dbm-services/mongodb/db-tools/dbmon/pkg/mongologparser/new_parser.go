package mongologparser

import "github.com/pkg/errors"

// MongoLogParser is an interface for parsing mongodb log
type MongoLogParser interface {
	Parse(data []byte) (*MongoLogMsg, error)
	Name() string
}

const slowLogId = 51803

// detectLogVersion detect log version.
// V1 : mongodb version 2.4
// V2 : mongodb version 3.0 - 4.2
// V3 : mongodb version 4.4 - 6.0 ...

const logVersionV1 = 1
const logVersionV2 = 2
const logVersionV3 = 3

type V1 struct {
}

func (v1 *V1) Parse(data []byte) (*MongoLogMsg, error) {
	return ParseV1Log(data)
}
func (v1 *V1) Name() string {
	return "v1"
}

type V2 struct {
}

func (v2 *V2) Parse(data []byte) (*MongoLogMsg, error) {
	return ParseV2Log(data)
}

func (v2 *V2) Name() string {
	return "v2"
}

type V3 struct {
}

func (v3 *V3) Parse(data []byte) (*MongoLogMsg, error) {
	v, _, err := ParseV3Mongolog(data)
	return v, err
}
func (v3 *V3) Name() string {
	return "v3"
}

func DetectVersion(firstChar byte) int {
	if firstChar == '{' {
		return logVersionV3
	} else if firstChar == '2' {
		return logVersionV2
	} else {
		return logVersionV1
	}
}

func GetParser(data []byte) (MongoLogParser, error) {
	if len(data) < 20 {
		return nil, errors.New("empty data")
	}
	v := DetectVersion(data[0])
	switch v {
	case logVersionV1:
		return &V1{}, nil
	case logVersionV2:
		return &V2{}, nil
	case logVersionV3:
		return &V3{}, nil
	}
	return nil, errors.New("DetectVersion error")
}
