package model

import (
	"testing"

	"bk-dbconfig/pkg/util/serialize"

	. "github.com/smartystreets/goconvey/convey"
)

func TestConfigVersionedPack(t *testing.T) {
	c := ConfigVersionedModel{}
	Convey("Test Serialize configs object", t, func() {
		configs := []*ConfigModel{
			{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c11"},
			{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "major_version", ConfValue: "mysql-5.7", LevelName: "module", LevelValue: "m10"},
			{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "mycnf_template", ConfValue: "my.cnf#55", LevelName: "module", LevelValue: "m20"},
		}
		vc := ConfigVersioned{Versioned: &c, Configs: configs, ConfigsDiff: nil}
		_ = vc.Pack()
		configsExpect := make([]*ConfigModel, 0)
		vc.Configs = nil // unpack wil set Configs
		_ = vc.UnPack()
		_ = serialize.UnSerializeString(c.ContentObj, &configsExpect, true)
		So(configs, ShouldResemble, vc.Configs)
	})
}
