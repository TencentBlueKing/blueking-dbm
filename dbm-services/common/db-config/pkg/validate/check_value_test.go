package validate

import (
	"bk-dbconfig/pkg/util"
	"log"
	"testing"

	. "github.com/smartystreets/goconvey/convey"
)

func BatchValidate(tvs [][4]string) int {
	var errList []error
	for _, tv := range tvs {
		if err := ValidateConfValue(tv[0], tv[1], tv[2], tv[3]); err != nil {
			errList = append(errList, err)
		}
	}
	log.Println("\n", util.SliceErrorsToError(errList))
	return len(errList)
}

func TestValidateConfValue(t *testing.T) {
	// [confValue, confType, confTypeSub, valueAllowed]

	Convey("Test conf_name conf_value validator", t, func() {
		Convey("Validate Enum", func() {
			valuesEnumSucc := [][4]string{
				{"1", "INT", "ENUM", "0|1|2"},
				{"1.1", "FLOAT", "ENUM", "1.1|2.1"},
				{"1", "STRING", "ENUM", "0|1"},
				{"ON", "STRING", "ENUM", "ON|OFF"},
				// {"", "STRING", "ENUM", "A|B|C|"},
				{"A,B", "STRING", "ENUMS", "A|B|C|"},
				{"C", "STRING", "ENUM", "A,B,C"},
				{"B", "STRING", "ENUM", "A, B, C"},
			}
			valuesEnumFail := [][4]string{
				{"3", "INT", "ENUM", "0|1|2"},
				{"1.2", "FLOAT", "ENUM", "1.1|2.1"},
				{"2", "STRING", "ENUM", "0|1"},
				{"on", "STRING", "ENUM", "ON|OFF"},
				{"D", "STRING", "ENUM", "A|B|C|"},
				{"A,D", "STRING", "ENUMS", "A|B|C|"},
			}
			errCount := BatchValidate(valuesEnumSucc)
			So(errCount, ShouldEqual, 0)
			errCount = BatchValidate(valuesEnumFail)
			So(errCount, ShouldEqual, len(valuesEnumFail))
		})

		Convey("Validate Range", func() {
			valuesRangeSucc := [][4]string{
				{"1", "INT", "RANGE", "[0,1]"},
				{"1.5", "FLOAT", "RANGE", "(0.0, 2.0]"},
				{"-2", "NUMBER", "RANGE", "[-2, 3.0]"},
			}
			valuesRangeFail := [][4]string{
				{"2", "INT", "RANGE", "[0,1]"},
				{"2.5", "FLOAT", "RANGE", "(0.0, 2.0]"},
				{"-2", "NUMBER", "RANGE", "(-2, 3.0]"},
			}
			errCount := BatchValidate(valuesRangeSucc)
			So(errCount, ShouldEqual, 0)
			errCount = BatchValidate(valuesRangeFail)
			So(errCount, ShouldEqual, len(valuesRangeFail))
		})

		Convey("Validate Bytes", func() {
			valuesSucc := [][4]string{
				{"1024", "STRING", "BYTES", "(0, 2048)"},
				{"1k", "STRING", "BYTES", "(0, 2048)"},
				{"64m", "STRING", "BYTES", "(0m, 1g)"},
				{"64m", "STRING", "BYTES", "64m | 128m"}, // enum
				{"1G", "STRING", "BYTES", "[0, 1024m]"},
			}
			valuesFail := [][4]string{
				{"0", "STRING", "BYTES", "(0, 2048)"},
				{"2g", "STRING", "BYTES", "(0, 2048k)"},
				{"1mBB", "STRING", "BYTES", "(0, 2048)"},
			}
			errCount := BatchValidate(valuesSucc)
			So(errCount, ShouldEqual, 0)
			errCount = BatchValidate(valuesFail)
			So(errCount, ShouldEqual, len(valuesFail))
		})
		Convey("Validate Duration", func() {
			valuesSucc := [][4]string{
				{"2m", "STRING", "DURATION", "(0, 5m)"},
				{"2h", "STRING", "DURATION", "(0, 2h]"},
				{"2d", "STRING", "DURATION", "(3600s, 7d]"},
				{"1w2d3m1s", "STRING", "DURATION", "[1d, 10d]"},
				{"2d", "STRING", "DURATION", "1d | 2d"}, // enum
			}
			valuesFail := [][4]string{
				{"2m", "STRING", "DURATION", "[2m1s, 5m)"},
				{"2h", "STRING", "DURATION", "[0s, 3600s]"},
			}
			errCount := BatchValidate(valuesSucc)
			So(errCount, ShouldEqual, 0)
			errCount = BatchValidate(valuesFail)
			So(errCount, ShouldEqual, len(valuesFail))
		})

		Convey("Validate Regex and Json", func() {
			valuesRegexSucc := [][4]string{
				{"0.0.0.0", "STRING", "REGEX", "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"},
				{"110", "STRING", "REGEX", "([1-9])|(110|120)"},
				{"{\"key\":\"value\"}", "STRING", "JSON", ""},
			}
			valuesRegexFail := [][4]string{
				{"0.0.0.0", "STRING", "REGEX", "172"},
				{"111", "STRING", "REGEX", "(^[1-9]$)|(^110$)|(^120$)"},
				{"110", "STRING", "REGEX", "(110"},
				{"{\"key\":\"value", "STRING", "JSON", ""},
			}
			errCount := BatchValidate(valuesRegexSucc)
			So(errCount, ShouldEqual, 0)
			errCount = BatchValidate(valuesRegexFail)
			So(errCount, ShouldEqual, len(valuesRegexFail))
		})

		Convey("Validate DataType", func() {
			valuesTypeFail := [][4]string{
				{"1", "INT", "JSON", "1"},
				{"ddd", "INT", "ENUM", ""},
			}
			errCount := BatchValidate(valuesTypeFail)
			So(errCount, ShouldEqual, len(valuesTypeFail))
		})
	})
}
