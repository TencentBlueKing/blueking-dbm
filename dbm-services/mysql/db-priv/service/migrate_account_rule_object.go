package service

var GcsDb *Database

type Count struct {
	AppUser
	Dbname string `json:"dbname" gorm:"column:dbname"`
	Cnt    int64  `json:"cnt" gorm:"column:cnt"`
}

type AppUser struct {
	App  string `json:"app" gorm:"column:app"`
	User string `json:"user" gorm:"column:user"`
}

// PrivModule scr、gcs账号规则的结构
type PrivModule struct {
	Uid        int64  `json:"uid" gorm:"column:uid"`
	App        string `json:"app" gorm:"column:app"`
	DbModule   string `json:"db_module" gorm:"column:db_module"`
	Module     string `json:"module" gorm:"column:module"`
	User       string `json:"user" gorm:"column:user"`
	Dbname     string `json:"dbname" gorm:"column:dbname"`
	Psw        string `json:"psw" gorm:"column:psw"`
	Privileges string `json:"privileges" gorm:"column:privileges"`
	Comment    string `json:"comment"  gorm:"column:comment"`
}

// MigratePara 迁移帐号规则的入参
type MigratePara struct {
	GcsDb DbConf `json:"gcs_db"`
	Apps  string `json:"apps" `
	Key   string `json:"key"`
	Mode  string `json:"mode"`
}

// DbConf 帐号规则所在数据库的配置
type DbConf struct {
	User string `json:"user"`
	Psw  string `json:"password"`
	Name string `json:"name"`
	Host string `json:"host"`
	Port string `json:"port"`
}
