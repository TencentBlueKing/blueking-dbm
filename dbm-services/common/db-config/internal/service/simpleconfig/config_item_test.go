package simpleconfig

import (
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"testing"

	. "github.com/smartystreets/goconvey/convey"
)

func GetConfigsExample() (configs []*model.ConfigModel) {
	configsExample := []*model.ConfigModel{
		{BKBizID: constvar.BKBizIDForPlat, Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: "default", LevelValue: constvar.LevelPlat},
		{BKBizID: constvar.BKBizIDForPlat, Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: "bk_biz_id", LevelValue: constvar.LevelPlat},

		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8mb4", LevelName: "bk_biz_id", LevelValue: "testapp"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: "module", LevelValue: "m10"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c11"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c12"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: "module", LevelValue: "m20"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: "cluster", LevelValue: "c21"},

		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "major_version", ConfValue: "mysql-5.7", LevelName: "bk_biz_id", LevelValue: "testapp"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "major_version", ConfValue: "mysql-5.7", LevelName: "module", LevelValue: "m10"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "major_version", ConfValue: "mysql-5.5", LevelName: "module", LevelValue: "m20"},

		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "mycnf_template", ConfValue: "MySQL-5.7", LevelName: "bk_biz_id", LevelValue: "testapp"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "mycnf_template", ConfValue: "MySQL-5.7", LevelName: "module", LevelValue: "m10"},
		{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "mycnf_template", ConfValue: "MySQL-5.5", LevelName: "module", LevelValue: "m20"},
	}
	return configsExample
}

func TestMergeConfig(t *testing.T) {
	Convey("Test Config Merge", t, func() {
		// replace function GetConfigLevelMap
		/*
		   configLevelStub := gomonkey.ApplyFunc(cst.GetConfigLevelMap, func() map[string]int {
		       return cst.ConfigLevelMap
		   })
		   defer configLevelStub.Reset()

		*/
		Convey("Get one conf_name item", func() {
			configs := []*model.ConfigModel{
				{BKBizID: constvar.BKBizIDForPlat, Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: constvar.LevelPlat, LevelValue: constvar.BKBizIDForPlat},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8mb4", LevelName: "app", LevelValue: "testapp"},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "gbk", LevelName: "module", LevelValue: "m10"},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c11"},
			}

			configMerged, err := MergeConfig(configs, constvar.ViewMerge)
			configsExpect1 := []*model.ConfigModel{
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c11"},
			}
			So(err, ShouldEqual, nil)
			So(configMerged, ShouldResemble, configsExpect1)
		})

		Convey("Get two conf_name item", func() {
			configs := []*model.ConfigModel{
				{BKBizID: constvar.BKBizIDForPlat, Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: constvar.LevelPlat, LevelValue: constvar.BKBizIDForPlat},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8mb4", LevelName: "app", LevelValue: "testapp"},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "major_version", ConfValue: "mysql-5.5", LevelName: "app", LevelValue: "testapp"},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c11"},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "major_version", ConfValue: "mysql-5.7", LevelName: "module", LevelValue: "m10"},
			}
			configMerged, _ := MergeConfig(configs, constvar.ViewMerge)
			configsExpect2 := []*model.ConfigModel{
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c11"},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "major_version", ConfValue: "mysql-5.7", LevelName: "module", LevelValue: "m10"},
			}
			So(configMerged, ShouldResemble, configsExpect2)
		})
	})
}

func TestCheckConfigItemWritable(t *testing.T) {
	Convey("Test ConfigItem writable", t, func() {

		upConfigs := []*model.ConfigModel{
			{BKBizID: constvar.BKBizIDForPlat, Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: constvar.LevelPlat, LevelValue: constvar.BKBizIDForPlat, FlagLocked: 0},
			{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "app", LevelValue: "testapp", FlagLocked: 0},
		}
		downConfigs := []*model.ConfigModel{
			{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "cluster", LevelValue: "c11", FlagLocked: 0},
		}
		currents := []*model.ConfigModel{
			{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "gbk", LevelName: "module", LevelValue: "m10", FlagLocked: 0},
			{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "gbk", LevelName: "module", LevelValue: "m10", FlagLocked: 1},
		}
		Convey("Has no any lock", func() {
			ret, err := CheckConfigItemWritable(currents[0], upConfigs, downConfigs)
			So(err, ShouldEqual, nil)
			So(len(*ret), ShouldEqual, 0)
		})
		Convey("Level module add lock1 (has remove)", func() {
			ret, err := CheckConfigItemWritable(currents[1], upConfigs, downConfigs)
			So(err, ShouldEqual, nil)
			removeRefCount := len((*ret)[constvar.OPTypeRemoveRef])
			So(removeRefCount, ShouldEqual, 1)
		})
		Convey("Level module add lock2 (no remove)", func() {
			downConfigs = nil
			ret, err := CheckConfigItemWritable(currents[1], upConfigs, downConfigs)
			So(err, ShouldEqual, nil)
			So(len(*ret), ShouldEqual, 0)
		})

		Convey("Level app has lock", func() {
			upConfigs := []*model.ConfigModel{
				{BKBizID: constvar.BKBizIDForPlat, Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "utf8", LevelName: constvar.LevelPlat, LevelValue: constvar.BKBizIDForPlat, FlagLocked: 0},
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "latin1", LevelName: "app", LevelValue: "testapp", FlagLocked: 1},
			}
			downConfigs := []*model.ConfigModel{}
			currents := []*model.ConfigModel{
				{BKBizID: "testapp", Namespace: "MySQL", ConfType: "deploy", ConfFile: "tb_app_info", ConfName: "charset", ConfValue: "gbk", LevelName: "module", LevelValue: "m10", FlagLocked: 0},
			}
			_, err := CheckConfigItemWritable(currents[0], upConfigs, downConfigs)
			So(err.Error(), ShouldContainSubstring, "已锁定配置")
		})
	})
}
