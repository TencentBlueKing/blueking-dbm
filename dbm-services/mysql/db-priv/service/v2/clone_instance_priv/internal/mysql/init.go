package mysql

var systemUsers []string

func init() {
	systemUsers = []string{
		"mysql.session", "mysql.sys", "mysql.infoschema", "mysql", //, "mariadb.sys", "PUBLIC",
	}
}
