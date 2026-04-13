package myredis

import (
	"testing"

	"dbm-services/redis/db-tools/dbactuator/mylog"

	"github.com/smartystreets/goconvey/convey"
)

func TestNeedSaveConfigRewriteWorkaroundByVersion(t *testing.T) {
	mylog.UnitTestInitLog()
	convey.Convey("need save config rewrite workaround by version", t, func() {
		need, err := needSaveConfigRewriteWorkaroundByVersion("6.0.16")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeTrue)

		need, err = needSaveConfigRewriteWorkaroundByVersion("6.2.1")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeTrue)

		need, err = needSaveConfigRewriteWorkaroundByVersion("6.2.2")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeFalse)

		need, err = needSaveConfigRewriteWorkaroundByVersion("7.0.0")
		convey.So(err, convey.ShouldBeNil)
		convey.So(need, convey.ShouldBeFalse)
	})
}

func TestFormatSaveConfigValue(t *testing.T) {
	mylog.UnitTestInitLog()
	convey.Convey("format save config value", t, func() {
		convey.So(formatSaveConfigValue(""), convey.ShouldEqual, `""`)
		convey.So(formatSaveConfigValue("   "), convey.ShouldEqual, `""`)
		convey.So(formatSaveConfigValue("900 1 300 10"), convey.ShouldEqual, "900 1 300 10")
		convey.So(formatSaveConfigValue(" 900 1 "), convey.ShouldEqual, "900 1")
	})
}
